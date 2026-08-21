# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Apply firewall preset use case.

Orchestrates the application of a predefined firewall policy (menu 3.4)
on a chosen backend: snapshots the current ruleset first (so it can be
restored later via menu restaure, then applies
the preset via the backend adapter.

Snapshot and state files are namespaced per backend (nftables vs
iptables): applying a preset on one backend must never overwrite or
invalidate the pending restore state of the other, since both can be
tested independently.

Conforms to Omega-Fire architecture charter:
- No direct subprocess calls (delegates entirely to the backend adapter,
  received already resolved by the caller)
- No hardcoded runtime paths (uses infrastructure/config/paths.py)
- Translates infrastructure exceptions into a structured result
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from omega_fire.domain.rules.presets import FirewallPreset
from omega_fire.infrastructure.config.paths import RUNTIME_DIR
from omega_fire.application.commands.backup_state import _collect_banned_ips, _collect_jails

def snapshot_file_for(backend: str) -> Path:
    """Get the snapshot file path for a specific backend.

    Args:
        backend: Backend label ('nftables' | 'iptables')

    Returns:
        Path to that backend's snapshot file, namespaced to avoid
        collision with the other backend's own snapshot.
    """
    return RUNTIME_DIR / f"preset_snapshot_{backend}.txt"


def state_file_for(backend: str) -> Path:
    """Get the active-preset state file path for a specific backend.

    Args:
        backend: Backend label ('nftables' | 'iptables')

    Returns:
        Path to that backend's state file.
    """
    return RUNTIME_DIR / f"active_preset_{backend}.json"


@dataclass
class ApplyPresetRequest:
    """Input for the apply preset use case."""
    preset: FirewallPreset
    backend: str


@dataclass
class ApplyPresetResult:
    """Output of the apply preset use case."""
    success: bool
    message: str


class ApplyPresetCommand:
    """Use case: snapshot the current ruleset, then apply a preset."""

    def __init__(
        self,
        firewall_adapter: Any,
        adapters: Optional[dict[str, Any]] = None,
        persistence_port: Any = None,
        rule_repository: Any = None,
    ):
        """Initialize the command.

        Args:
            firewall_adapter: Already-resolved backend adapter (nftables or
                iptables), matching request.backend. Must expose
                dump_ruleset() and apply_preset().
            adapters: Optional mapping of ALL resolved backend adapters
                (nftables, iptables, ip6tables, fail2ban), used to
                capture a multi-backend snapshot before applying the
                profile. If None, that capture is skipped (rétrocompatible).
            persistence_port: Optional PersistencePort implementation,
                used to store the multi-backend snapshot with
                origin="auto_preset". If None, the capture is skipped.
            rule_repository: Optional RuleRepository instance, used to
                keep the database in sync with the rules the profile
                actually applies. If None, that sync is skipped.
        """
        self._adapter = firewall_adapter
        self._adapters = adapters
        self._persistence_port = persistence_port
        self._rule_repository = rule_repository

    def execute(self, request: ApplyPresetRequest) -> ApplyPresetResult:
        if self._adapter is None:
            return ApplyPresetResult(
                success=False,
                message=f"Aucun backend disponible pour appliquer un profil sur {request.backend}.",
            )

        snapshot_file = snapshot_file_for(request.backend)
        state_file = state_file_for(request.backend)
        warnings: list[str] = []

        # --- 1. Snapshot de l'état actuel de CE backend (avant modification) ---
        try:
            current_ruleset = self._adapter.dump_ruleset()
        except Exception as e:
            return ApplyPresetResult(
                success=False,
                message=f"Impossible de sauvegarder l'état actuel avant application : {e}. "
                        f"Application annulée par sécurité.",
            )

        try:
            RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            snapshot_file.write_text(current_ruleset, encoding="utf-8")
        except Exception as e:
            return ApplyPresetResult(
                success=False,
                message=f"Impossible d'écrire le fichier de sauvegarde ({e}). "
                        f"Application annulée par sécurité.",
            )

        # --- 1b. Snapshot complet multi-backend (nouveau, non bloquant) ---
        # Capture l'état AVANT le flush du profil, avec origin="auto_preset",
        # pour que 7.2 puisse voir et restaurer cet état même si un profil
        # était actif au moment de la sauvegarde. N'annule jamais
        # l'application du profil si elle échoue — seulement signalé en fin
        # de message.
        if self._persistence_port is not None and self._adapters is not None:
            try:
                self._capture_full_snapshot(request)
            except Exception as e:
                warnings.append(f"snapshot complet non créé ({e})")

        # --- 2. Application du profil ---
        try:
            self._adapter.apply_preset(request.preset)
        except Exception as e:
            return ApplyPresetResult(
                success=False,
                message=f"Échec de l'application du profil '{request.preset.name}' sur "
                        f"{request.backend} : {e}. L'état antérieur reste disponible via [R].",
            )

        # --- 2b. Synchronisation RuleRepository (non bloquant) ---
        # Le profil vient de tout flusher sur ce backend : les anciennes
        # lignes trackées (managed ou imported) ne correspondent plus à
        # rien de vivant. On les retire, puis on persiste les règles
        # réellement posées par le profil (external_ref garanti exact,
        # lu directement depuis le live après application).
        if self._rule_repository is not None:
            try:
                self._sync_repository_with_backend(request.backend)
            except Exception as e:
                warnings.append(f"base de données non synchronisée ({e})")

        # --- 3. Enregistrement de l'état actif (propre à ce backend) ---
        # rules_count_at_apply : nombre de règles managées réellement
        # posées par ce profil, lu juste après la synchronisation du
        # repository ci-dessus (base déjà à jour). Utilisé par le
        # dashboard (menu 8.1) pour détecter une divergence ultérieure
        # (ajout via 3.1 ou suppression via 3.2) — best-effort, son
        # absence ne bloque jamais l'application du profil.
        rules_count_at_apply = None
        if self._rule_repository is not None:
            try:
                rules_count_at_apply = self._rule_repository.count_managed(request.backend)
            except Exception:
                rules_count_at_apply = None

        try:
            RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            state_file.write_text(
                json.dumps({
                    "active_preset": request.preset.key,
                    "backend": request.backend,
                    "applied_at": datetime.now().isoformat(),
                    "rules_count_at_apply": rules_count_at_apply,
                }),
                encoding="utf-8",
            )
        except Exception:
            return ApplyPresetResult(
                success=True,
                message=f"Le profil '{request.preset.name}' a été appliqué sur {request.backend}, "
                        f"mais son état n'a pas pu être enregistré (l'indicateur ACTIF pourrait "
                        f"être incorrect au prochain affichage).",
            )
        message = f"Le profil '{request.preset.name}' est maintenant actif sur {request.backend}."
        if warnings:
            message += " Avertissement : " + " ; ".join(warnings) + "."

        return ApplyPresetResult(
            success=True,
            message=message,
        )

        # --- 2. Application du profil ---
        try:
            self._adapter.apply_preset(request.preset)
        except Exception as e:
            return ApplyPresetResult(
                success=False,
                message=f"Échec de l'application du profil '{request.preset.name}' sur "
                        f"{request.backend} : {e}. L'état antérieur reste disponible via [R].",
            )

        # --- 3. Enregistrement de l'état actif (propre à ce backend) ---
        try:
            RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            state_file.write_text(
                json.dumps({
                    "active_preset": request.preset.key,
                    "backend": request.backend,
                    "applied_at": datetime.now().isoformat(),
                }),
                encoding="utf-8",
            )
        except Exception:
            return ApplyPresetResult(
                success=True,
                message=f"Le profil '{request.preset.name}' a été appliqué sur {request.backend}, "
                        f"mais son état n'a pas pu être enregistré (l'indicateur ACTIF pourrait "
                        f"être incorrect au prochain affichage).",
            )

        return ApplyPresetResult(
            success=True,
            message=f"Le profil '{request.preset.name}' est maintenant actif sur {request.backend}.",
        )
    
    def _capture_full_snapshot(self, request: ApplyPresetRequest) -> None:
        """Capture l'état complet (tous backends) juste avant le flush du
        profil, et le sauvegarde via persistence_port avec
        origin="auto_preset". Réutilise les mêmes collecteurs que le
        menu 7.1 (application/commands/backup_state.py) pour rester
        cohérent avec ce que 7.2 sait déjà lire.
        """
        banned_ips = _collect_banned_ips({
            k: v for k, v in self._adapters.items()
            if k in ("nftables", "iptables", "ip6tables", "fail2ban")
        })

        rules = []
        for backend_name in ("nftables", "iptables", "ip6tables"):
            backend_adapter = self._adapters.get(backend_name)
            if backend_adapter is None:
                continue
            try:
                rules.extend(backend_adapter.list_rules())
            except Exception:
                continue

        jails = _collect_jails(self._adapters.get("fail2ban"))

        self._persistence_port.create_snapshot(
            banned_ips=banned_ips,
            rules=rules,
            jails=jails,
            description=(
                f"Auto — avant application du profil '{request.preset.name}' "
                f"sur {request.backend}"
            ),
            origin="auto_preset",
        )

    def _sync_repository_with_backend(self, backend: str) -> None:
        """Resynchronise RuleRepository avec l'état réel de CE backend
        après application d'un profil.

        apply_preset() flush entièrement le backend avant d'appliquer
        (voir infrastructure/backends/{nftables,iptables}/adapter.py) :
        toutes les anciennes lignes de ce backend en base — managed ET
        imported confondues — ne correspondent plus à rien de vivant.
        On les retire, puis on persiste chaque règle réellement posée
        par le profil, lue directement depuis le live (external_ref
        déjà exact, peuplé par le mapper du backend — pas de matching
        heuristique nécessaire ici, contrairement à restore_state.py).

        Cas particulier nftables : NftablesAdapter.list_rules() balaie
        volontairement TOUTES les tables/familles du live (pas
        seulement 'inet filter', propre à Omega-Fire) — nécessaire
        ailleurs (menu 3.3, badge "SYSTÈME") pour détecter les règles
        posées par un autre outil. Depuis que apply_preset() ne flush
        plus que sa propre table (voir NftablesAdapter.apply_preset()),
        la table 'ip filter' gérée par iptables-nft peut coexister et
        remonte donc, elle aussi, dans list_rules(). Sans filtre ici,
        ces règles seraient à tort marquées origin="managed" sous
        backend="nftables", alors qu'elles sont déjà trackées
        correctement sous backend="iptables" par ce même mécanisme
        appliqué à CE backend — d'où un doublon complet observé en
        test réel.
        Seules les règles vivant réellement dans la table qu'Omega-Fire
        vient d'écrire (family="inet", table="filter" — mêmes valeurs
        que celles utilisées par NftablesAdapter.apply_preset()) sont
        conservées ici.
        """
        stale_rules = self._rule_repository.find_all(backend=backend)
        for stale_rule in stale_rules:
            try:
                self._rule_repository.delete(stale_rule.rule_id)
            except Exception:
                pass

        live_rules = self._adapter.list_rules()

        if backend == "nftables":
            live_rules = [
                r for r in live_rules
                if getattr(getattr(r, "family", None), "value", None) == "inet"
                and (r.table_name or "filter") == "filter"
            ]

        for live_rule in live_rules:
            live_rule.origin = "managed"
            try:
                self._rule_repository.save(live_rule)
            except Exception:
                pass

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Sauvegarde l'état actuel du ruleset (snapshot texte), puis applique un
#   profil prédéfini (domain/rules/presets.py) via l'adapter du backend
#   choisi par l'utilisateur (menu 3.4).
# - Enregistre quel profil est actif, pour l'affichage (badge ACTIF) et
#   pour la restauration ultérieure.
#
# Pourquoi dans application/commands/ (charte) :
# - Cas d'usage qui orchestre snapshot + application + état.
# - Ne fait aucun subprocess direct (délégué à l'adapter).
# - Ne code aucun chemin en dur (RUNTIME_DIR vient de infrastructure/config/paths.py).
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (adapter reçu en paramètre)
# ❌ Pas de rendu UI
# ❌ Pas de connaissance de la syntaxe nft/iptables (déléguée à l'adapter)
#
# Points clés :
# - snapshot_file_for(backend) / state_file_for(backend) : chemins
#   NAMESPACÉS par backend (var/runtime/preset_snapshot_nftables.txt vs
#   preset_snapshot_iptables.txt, idem pour l'état actif) — appliquer un
#   profil sur un backend n'écrase jamais l'état de restauration de
#   l'autre backend, ce qui permet de tester les deux indépendamment sans
#   perdre la possibilité de revenir en arrière sur l'un ou l'autre
# - Sécurité : si le snapshot ne peut pas être sauvegardé, le profil n'est
#   JAMAIS appliqué (rien ne se modifie rien sans pouvoir garantir un retour arrière)
# - RUNTIME_DIR.mkdir(parents=True, exist_ok=True) avant chaque écriture :
#   robuste même si var/ a été vidé par un nettoyage avancé de l'appli
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_3_4_apply_preset(ctx)
#   ↓ résout l'adapter via ctx.container.get_firewall_port(backend)
#   ↓ récupère le preset via domain/rules/presets.py (get_preset(key))
# application/commands/apply_preset.py : ApplyPresetCommand.execute()
#   ↓ adapter.dump_ruleset() / adapter.apply_preset()
#---------------------------------------------------------------------->
