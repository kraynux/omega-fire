# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Nettoyage-synchronisation de la table des regles (menu 3.2).

Remet la base d'accord avec les backends tels qu'ils sont sur la machine, sans
jamais toucher au pare-feu (aucune commande noyau : seulement list_rules()).
Retour utilisateur 2026-10-28 : 564 lignes en base pour 72 regles distinctes,
restes d'une restauration 7.2 et d'imports successifs ; chaque machine ayant ses
propres regles (UFW, Tailscale, docker...), on repart de ce que le noyau contient
vraiment plutot que de corriger au cas par cas.

Deux temps :
- plan() : lit chaque backend et classe les lignes de la base (a garder,
  doublons, absentes du noyau, backend absent) et les regles du noyau inconnues ;
- apply(plan) : sauvegarde la base, retire les lignes classees, importe les
  regles manquantes, reactive les lignes gardees.

Une regle est reconnue a son identite technique : backend + famille + table +
external_ref (handle nft, unique par table seulement ; ligne -S complete pour
iptables/ip6tables). L'origine « managed » est gardee quand la regle est
toujours dans le noyau.

Backend dont la lecture echoue (droits, erreur) : ses lignes ne sont JAMAIS
touchees — seule une lecture reussie fait foi. Backend absent de la machine
(binaire introuvable, adapter None) : ses lignes sont retirees.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from omega_fire.infrastructure.storage.sqlite.exceptions import RepositoryError
from omega_fire.shared.i18n import _

KNOWN_BACKENDS = ("nftables", "iptables", "ip6tables")


def rule_identity(rule: Any) -> tuple | None:
    """Identite technique d'une regle (base ou noyau) ; None sans external_ref."""
    ref = getattr(rule, "external_ref", None)
    if not ref:
        return None
    backend = getattr(rule, "backend", "")
    if backend == "nftables":
        family = getattr(rule, "family", "")
        family = getattr(family, "value", family)
        return (backend, str(family), str(getattr(rule, "table_name", "")), str(ref))
    return (backend, str(ref))


@dataclass
class ReconcilePlan:
    """Apercu du nettoyage (rien n'est encore modifie)."""
    keep: list = field(default_factory=list)
    duplicates: list = field(default_factory=list)
    stale: list = field(default_factory=list)
    unavailable: list = field(default_factory=list)
    to_import: list = field(default_factory=list)
    to_enable: list = field(default_factory=list)
    unreadable: dict[str, str] = field(default_factory=dict)
    live_counts: dict[str, int] = field(default_factory=dict)

    @property
    def to_remove(self) -> list:
        return self.duplicates + self.stale + self.unavailable

    @property
    def has_changes(self) -> bool:
        return bool(self.to_remove or self.to_import or self.to_enable)


@dataclass
class ReconcileResult:
    success: bool
    removed: int = 0
    imported: int = 0
    enabled: int = 0
    backup_path: Path | None = None
    message: str = ""


class ReconcileRulesCommand:
    def __init__(self, rule_repository: Any, backup_dir: Path) -> None:
        self._repository = rule_repository
        self._backup_dir = backup_dir

    def plan(self, backends: dict[str, Any]) -> ReconcilePlan:
        """backends : nom -> adapter, ou None si le backend est absent de la machine.
        Un backend connu non fourni est traite comme absent."""
        plan = ReconcilePlan()
        live_by_backend: dict[str, list] = {}
        for name in KNOWN_BACKENDS:
            adapter = backends.get(name)
            if adapter is None:
                live_by_backend[name] = []
                continue
            try:
                live_by_backend[name] = list(adapter.list_rules())
            except Exception as e:
                plan.unreadable[name] = str(e) or e.__class__.__name__

        db_rules = sorted(self._repository.find_all(), key=lambda r: r.rule_id)
        for name, live_rules in live_by_backend.items():
            plan.live_counts[name] = len(live_rules)
            absent = backends.get(name) is None
            rows = [r for r in db_rules if r.backend == name]

            # Combien d'exemplaires de chaque regle le noyau contient (deux lignes
            # iptables identiques sont deux regles).
            live_count = Counter(rule_identity(r) for r in live_rules)
            live_count.pop(None, None)
            first_live = {}
            for r in live_rules:
                first_live.setdefault(rule_identity(r), r)

            by_identity: dict[tuple | None, list] = {}
            for r in rows:
                by_identity.setdefault(rule_identity(r), []).append(r)

            for identity, group in by_identity.items():
                if absent:
                    plan.unavailable.extend(group)
                    continue
                wanted = live_count.get(identity, 0) if identity is not None else 0
                if wanted == 0:
                    plan.stale.extend(group)
                    continue
                # Garder d'abord les lignes « managed » (creees par Omega-Fire), puis
                # les plus anciennes.
                group = sorted(group, key=lambda r: (r.origin != "managed", r.rule_id))
                kept, extra = group[:wanted], group[wanted:]
                plan.keep.extend(kept)
                plan.duplicates.extend(extra)
                plan.to_enable.extend(r for r in kept if not r.enabled)

            for identity, count in live_count.items():
                known = len(by_identity.get(identity, ())) if not absent else 0
                for _i in range(max(0, count - known)):
                    plan.to_import.append(first_live[identity])

        return plan

    def apply(self, plan: ReconcilePlan) -> ReconcileResult:
        if not plan.has_changes:
            return ReconcileResult(success=True, message=_("La base est déjà propre : rien à changer."))
        try:
            self._backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = self._backup_dir / f"omega_{datetime.now():%Y%m%d_%H%M%S}.db"
            self._repository.backup_database(backup_path)
        except Exception as e:
            return ReconcileResult(
                success=False,
                message=_("Sauvegarde de la base impossible, rien n'a été modifié : {e}").format(e=e),
            )

        removed = imported = enabled = 0
        try:
            for r in plan.to_remove:
                if self._repository.delete(r.rule_id):
                    removed += 1
            for r in plan.to_import:
                r.origin = "imported"
                r.enabled = True
                self._repository.save(r)
                imported += 1
            for r in plan.to_enable:
                if self._repository.update_enabled(r.rule_id, True):
                    enabled += 1
        except RepositoryError as e:
            return ReconcileResult(
                success=False, removed=removed, imported=imported, enabled=enabled,
                backup_path=backup_path,
                message=_("Erreur technique pendant le nettoyage : {e}. Sauvegarde : {path}").format(e=e, path=backup_path),
            )

        return ReconcileResult(
            success=True, removed=removed, imported=imported, enabled=enabled,
            backup_path=backup_path,
            message=_("Base nettoyée : {removed} ligne(s) retirée(s), {imported} règle(s) importée(s), {enabled} réactivée(s). Pare-feu non modifié. Sauvegarde : {path}").format(
                removed=removed, imported=imported, enabled=enabled, path=backup_path,
            ),
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Nettoyage-synchronisation de la table rules avec les backends réels
#   (menu 3.2, option « Nettoyer et resynchroniser la base »).
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration lecture backends + comparaison + écriture base.
# - Aucun subprocess, aucun SQL brut, aucune commande d'écriture noyau.
#
# Garde-fous :
# - Lecture en échec = backend illisible, ses lignes ne sont pas touchées.
# - Sauvegarde de omega.db (API backup SQLite) avant toute écriture.
# - Jamais de flush : seule la base change.
#----------------------------------------------------------------------
