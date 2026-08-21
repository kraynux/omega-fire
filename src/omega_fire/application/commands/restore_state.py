# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Restore state command.

Orchestrates the restoration of a full-state snapshot (menu 7.2):
- Rules: FULL REPLACEMENT. Every rule currently tracked by Omega-Fire
  (has an external_ref in RuleRepository) is removed from the live
  kernel and from the database, then every rule from the snapshot is
  reapplied. This never touches rules NOT tracked by Omega-Fire (e.g.
  UFW or other tools' rules), since only tracked external_refs are
  targeted — no system-wide flush.
- Banned IPs: ADD-ONLY. Only IPs missing from the current live state
  are added; nothing is ever removed. This is deliberately asymmetric
  with rules — action_2_1_ban_ip does not persist bans to the database,
  so there is no reliable way to distinguish Omega-Fire-managed bans
  from others, making a safe targeted removal impossible for IPs.
- Fail2ban jails: reported for information only, never restored
  automatically (would require the full jail creation wizard, menu 4.4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from omega_fire.application.commands.apply_preset import state_file_for


@dataclass
class RestoreStateRequest:
    """Input for the restore state use case."""
    snapshot_id: str


@dataclass
class RestoreStateResult:
    """Output of the restore state use case."""
    success: bool
    message: str
    rules_removed: int = 0
    rules_applied: int = 0
    ips_added: int = 0
    ips_already_present: int = 0
    jails_in_snapshot: int = 0
    errors: list[str] = field(default_factory=list)


class RestoreStateCommand:
    """Use case: restore a snapshot — rules replaced entirely, IPs
    added only, jails reported only."""

    def __init__(
        self,
        persistence_port: Any,
        adapters: dict[str, Any],
        rule_repository: Any,
    ):
        """Initialize the command.

        Args:
            persistence_port: FileBackupAdapter instance (needs
                get_snapshot_content()).
            adapters: mapping of backend name -> resolved adapter
                (nftables, iptables, ip6tables, fail2ban).
            rule_repository: RuleRepository instance, needed to find
                and remove currently tracked rules before reapplying.
        """
        self._port = persistence_port
        self._adapters = adapters
        self._rule_repository = rule_repository

    def execute(self, request: RestoreStateRequest) -> RestoreStateResult:
        domain_snapshot = self._port.get_snapshot_content(request.snapshot_id)
        if domain_snapshot is None:
            return RestoreStateResult(
                success=False,
                message=f"Snapshot introuvable : {request.snapshot_id}",
            )

        errors: list[str] = []

        # Capture des règles trackées AVANT toute modification. Fige
        # l'état "ancien" à retirer une fois les nouvelles règles en
        # place — indispensable car _apply_snapshot_rules() ci-dessous
        # insère de nouvelles lignes dans RuleRepository au fur et à
        # mesure : une relecture de find_all() APRÈS cette étape
        # verrait aussi les règles tout juste appliquées et les
        # retirerait par erreur.
        try:
            rules_to_remove = self._rule_repository.find_all() if self._rule_repository else []
        except Exception as e:
            errors.append(f"Impossible de lire les règles trackées : {e}")
            rules_to_remove = []

        # Ordre volontaire : APPLIQUER les nouvelles règles avant de
        # RETIRER les anciennes. Ça garantit qu'il n'existe jamais un
        # instant où la chaîne n'a AUCUNE règle — ce qui, avec une
        # politique par défaut DROP, bloquerait tout le trafic entrant
        # pendant la transition. Les nouvelles règles coexistent
        # brièvement avec les anciennes (state transitoire sans danger,
        # nftables tolère les doublons), puis les anciennes — et
        # seulement les anciennes, capturées ci-dessus — sont retirées
        # une fois les nouvelles en place.
        rules_applied = self._apply_snapshot_rules(domain_snapshot, errors)
        rules_removed = self._remove_tracked_rules(rules_to_remove, errors)
        self._reset_chain_policies(errors)
        ips_added, ips_present = self._restore_ips_add_only(domain_snapshot, errors)
        

        jails_count = domain_snapshot.content.fail2ban.count if domain_snapshot.content.fail2ban else 0

        # Une restauration d'état complet invalide sémantiquement toute
        # notion de "profil actif" (3.4) : les règles ont été remplacées
        # sous ses pieds, sans passer par apply_preset(). Nettoyage
        # inconditionnel des deux backends plutôt que de tenter de
        # déterminer finement lequel a été touché — mieux vaut un badge
        # "Aucun profil actif" trop prudent qu'un badge ACTIF mensonger.
        self._clear_preset_markers()

        return RestoreStateResult(
            success=True,
            message="Restauration terminée : règles remplacées, IPs ajoutées (jamais retirées).",
            rules_removed=rules_removed,
            rules_applied=rules_applied,
            ips_added=ips_added,
            ips_already_present=ips_present,
            jails_in_snapshot=jails_count,
            errors=errors,
        )

    def _remove_tracked_rules(self, tracked_rules: list, errors: list[str]) -> int:
        """Remove every rule tracked by Omega-Fire BEFORE this
        restoration started (captured by execute() prior to calling
        _apply_snapshot_rules(), passed in here as tracked_rules) from
        the live kernel, then from the database. Never touches rules
        Omega-Fire never tracked (other tools), and never touches
        rules this same restoration just inserted — see execute() for
        why that distinction is critical.

        Stale rows (external_ref no longer present in the live state —
        common after repeated testing/manual kernel changes) are
        silently cleaned up from the database rather than logged as
        errors: the goal (rule absent from live state) is already met.
        """
        if self._rule_repository is None or not tracked_rules:
            return 0

        # Pré-charger l'état live par backend pour vérifier l'existence
        # réelle des handles avant de tenter une suppression.
        live_refs_by_backend: dict[str, set[str]] = {}
        for backend, adapter in self._adapters.items():
            if adapter is None:
                continue
            try:
                live_rules = adapter.list_rules()
                live_refs_by_backend[backend] = {
                    str(getattr(r, "external_ref", "")) for r in live_rules
                    if getattr(r, "external_ref", None)
                }
            except Exception:
                continue

        removed = 0
        for rule in tracked_rules:
            ref = getattr(rule, "external_ref", None)
            if not ref:
                continue

            backend = getattr(rule, "backend", None)
            adapter = self._adapters.get(backend)
            if adapter is None:
                continue

            # Handle déjà absent du live : nettoyage silencieux, pas une erreur.
            if backend in live_refs_by_backend and str(ref) not in live_refs_by_backend[backend]:
                try:
                    self._rule_repository.delete(getattr(rule, "rule_id", None))
                except Exception:
                    pass
                continue

            try:
                if backend == "nftables":
                    handle = int(ref)
                    ok = adapter.delete_rule(
                        family=rule.family.value if hasattr(rule.family, "value") else "inet",
                        table=rule.table_name or "filter",
                        chain=rule.chain.value,
                        handle=handle,
                    )
                elif backend in ("iptables", "ip6tables"):
                    # ip6tables expose delete_rule_by_content() avec la
                    # même signature qu'iptables (miroir mécanique,
                    # référentiel §53) — pas de branche dédiée nécessaire.
                    ok = adapter.delete_rule_by_content(ref)
                else:
                    continue

                if ok:
                    self._rule_repository.delete(getattr(rule, "rule_id", None))
                    removed += 1
            except Exception as e:
                # Une règle déjà absente du noyau (No such file or
                # directory) atteint déjà l'objectif visé — nettoyage
                # silencieux de la ligne en base, pas une vraie erreur.
                error_text = str(e).lower()
                if "no such file or directory" in error_text or "could not process rule" in error_text:
                    try:
                        self._rule_repository.delete(getattr(rule, "rule_id", None))
                    except Exception:
                        pass
                else:
                    errors.append(f"Erreur suppression règle ({backend}) : {e}")

        return removed

    def _apply_snapshot_rules(self, domain_snapshot, errors: list[str]) -> int:
        """Apply every rule stored in the snapshot to the live backends,
        and persist each successfully applied rule to RuleRepository so
        the database stays in sync with the kernel — mirroring what
        CreateRuleCommand does for menu 3.1. Without this, the database
        never learns about rules applied here, causing menu 3.3 to
        re-import them as "new" on every subsequent scan (observed
        during session testing: rules table grew to 800+ rows for a
        12-rule live ruleset)."""
        if not domain_snapshot.content.rules:
            return 0
        # Trie par 'order' (position réelle dans le noyau au moment de
        # la capture) — respecter cet ordre est critique : une règle
        # DROP sans condition, appliquée avant les règles ACCEPT,
        # bloquerait tout le trafic quel que soit ce qui suit.
        rules_to_apply = sorted(
            domain_snapshot.content.rules.rules,
            key=lambda r: r.get("order", 0),
        )
        applied = 0
        for rule_data in rules_to_apply:
            backend = rule_data.get("backend")
            adapter = self._adapters.get(backend)
            if adapter is None:
                continue

            port = rule_data.get("port")
            if port in (None, "", "*"):
                port = None

            try:
                if backend == "nftables":
                    ok = adapter.add_rule(
                        family="inet",
                        table="filter",
                        chain=rule_data.get("chain"),
                        action=rule_data.get("action"),
                        protocol=rule_data.get("protocol"),
                        port=port,
                        source=rule_data.get("source"),
                        destination=rule_data.get("destination"),
                        comment=rule_data.get("comment") or "",
                    )
                elif backend in ("iptables", "ip6tables"):
                    # ip6tables expose add_rule() avec la même signature
                    # qu'iptables (miroir mécanique, référentiel §53) —
                    # pas de branche dédiée nécessaire.
                    ok = adapter.add_rule(
                        chain=str(rule_data.get("chain", "")).upper(),
                        action=rule_data.get("action"),
                        protocol=rule_data.get("protocol"),
                        port=port,
                        source=rule_data.get("source"),
                        destination=rule_data.get("destination"),
                        comment=rule_data.get("comment") or "",
                    )
                else:
                    continue

                if ok:
                    applied += 1
                    self._persist_applied_rule(backend, rule_data, adapter)
                else:
                    errors.append(f"Règle non appliquée ({backend}) : {rule_data.get('comment', '?')}")
            except Exception as e:
                errors.append(f"Erreur application règle ({backend}) : {e}")

        return applied

    def _persist_applied_rule(self, backend: str, rule_data: dict, adapter: Any) -> None:
        """Persist a successfully applied rule to RuleRepository,
        finding its external_ref by re-reading the live state — same
        approach as CreateRuleCommand._find_applied_external_ref()."""
        if self._rule_repository is None:
            return

        try:
            from omega_fire.domain.rules.models import (
                FirewallRule, RuleAction, RuleChain, RuleFamily, RuleProtocol,
            )

            action_map = {"drop": RuleAction.DROP, "reject": RuleAction.REJECT, "accept": RuleAction.ACCEPT}
            chain_map = {"input": RuleChain.INPUT, "forward": RuleChain.FORWARD, "output": RuleChain.OUTPUT}
            protocol_map = {"tcp": RuleProtocol.TCP, "udp": RuleProtocol.UDP, "icmp": RuleProtocol.ICMP}

            rule_action = action_map.get(str(rule_data.get("action", "")).lower(), RuleAction.DROP)
            rule_chain = chain_map.get(str(rule_data.get("chain", "")).lower(), RuleChain.INPUT)
            rule_protocol = protocol_map.get(str(rule_data.get("protocol", "")).lower())

            port_raw = rule_data.get("port")
            port_val = None
            if port_raw not in (None, "", "*"):
                try:
                    port_val = int(port_raw)
                except (TypeError, ValueError):
                    port_val = None

            family_by_backend = {
                "nftables": RuleFamily.INET,
                "iptables": RuleFamily.IP,
                "ip6tables": RuleFamily.IP6,
            }
            rule = FirewallRule(
                backend=backend,
                family=family_by_backend.get(backend, RuleFamily.INET),
                table_name="filter",
                chain=rule_chain,
                action=rule_action,
                protocol=rule_protocol,
                port_start=port_val,
                port_end=port_val,
                source_cidr=rule_data.get("source"),
                dest_cidr=rule_data.get("destination"),
                comment=rule_data.get("comment") or "",
                enabled=True,
                origin="managed",
            )

            new_id = self._rule_repository.save(rule)

            try:
                live_rules = adapter.list_rules()
                matches = [
                    lr for lr in live_rules
                    if lr.chain == rule_chain
                    and lr.action.value == rule_action.value.lower()
                    and lr.protocol == rule_protocol
                    and lr.port_start == port_val
                    and (getattr(lr, "source_cidr", None) or None) == (rule_data.get("source") or None)
                ]
                if matches:
                    def _ref_as_int(m):
                        try:
                            return int(m.external_ref)
                        except (TypeError, ValueError):
                            return -1
                    best_match = max(matches, key=_ref_as_int)
                    self._rule_repository.update_external_ref(new_id, best_match.external_ref)
            except Exception:
                pass

        except Exception:
            pass

    def _restore_ips_add_only(self, domain_snapshot, errors: list[str]) -> tuple[int, int]:
        """Add banned IPs from the snapshot that are missing from the
        live state. Never removes any existing ban."""
        if not domain_snapshot.content.blacklist:
            return 0, 0

        added = 0
        already_present = 0

        live_ips_by_backend: dict[str, set[str]] = {}
        for backend, adapter in self._adapters.items():
            if adapter is None:
                continue
            try:
                if hasattr(adapter, "list_bans"):
                    raw = adapter.list_bans()
                elif hasattr(adapter, "list_banned_ips"):
                    raw = adapter.list_banned_ips()
                else:
                    continue
            except Exception:
                continue

            ips = set()
            for item in raw:
                ip = item.get("ip") if isinstance(item, dict) else getattr(item, "ip", None)
                if ip:
                    ips.add(str(ip).split("/")[0].strip())
            live_ips_by_backend[backend] = ips

        for entry in domain_snapshot.content.blacklist.banned_ips:
            ip = entry.get("ip")
            backend = entry.get("backend")
            if not ip or backend not in live_ips_by_backend:
                continue

            if ip in live_ips_by_backend[backend]:
                already_present += 1
                continue

            adapter = self._adapters.get(backend)
            if adapter is None:
                continue

            try:
                comment = entry.get("comment") or "Restauré depuis snapshot"
                if hasattr(adapter, "ban_ip"):
                    ok = adapter.ban_ip(ip=ip, comment=comment)
                elif hasattr(adapter, "ban"):
                    ok = adapter.ban(ip=ip, comment=comment)
                else:
                    continue

                if ok:
                    added += 1
                    live_ips_by_backend[backend].add(ip)
                else:
                    errors.append(f"IP non restaurée ({backend}) : {ip}")
            except Exception as e:
                errors.append(f"Erreur IP {ip} ({backend}) : {e}")

        return added, already_present

    def _reset_chain_policies(self, errors: list[str]) -> None:
        """Remet la politique par défaut des chaînes de base (input,
        output, forward) à ACCEPT sur chaque backend disponible.

        Une restauration ne fait que retirer/réappliquer des règles
        individuelles — jamais la politique par défaut d'une chaîne.
        Si un profil (menu 3.4) avait laissé une chaîne en policy DROP,
        cette politique survivrait à la restauration même une fois
        toutes ses règles retirées, bloquant tout paquet qui ne
        correspond à aucune règle explicite.
        """
        chain_names = ("input", "output", "forward")

        nft_adapter = self._adapters.get("nftables")
        if nft_adapter is not None:
            for chain_name in chain_names:
                try:
                    nft_adapter.set_chain_policy(chain_name, policy="accept")
                except Exception as e:
                    errors.append(f"Politique non réinitialisée (nftables/{chain_name}) : {e}")

        ipt_adapter = self._adapters.get("iptables")
        if ipt_adapter is not None:
            for chain_name in chain_names:
                try:
                    ipt_adapter.set_chain_policy(chain_name, policy="ACCEPT")
                except Exception as e:
                    errors.append(f"Politique non réinitialisée (iptables/{chain_name}) : {e}")

        ip6t_adapter = self._adapters.get("ip6tables")
        if ip6t_adapter is not None:
            for chain_name in chain_names:
                try:
                    ip6t_adapter.set_chain_policy(chain_name, policy="ACCEPT")
                except Exception as e:
                    errors.append(f"Politique non réinitialisée (ip6tables/{chain_name}) : {e}")

    def _clear_preset_markers(self) -> None:
        """Supprime les marqueurs 'profil actif' (3.4) des deux backends,
        s'ils existent. Best-effort et silencieux : l'échec de ce
        nettoyage cosmétique ne doit jamais faire échouer une
        restauration qui a par ailleurs réussi — au pire, 3.4 affichera
        un badge ACTIF obsolète jusqu'à la prochaine application de
        profil, ce qui reste sans danger opérationnel.
        """
        for backend in ("nftables", "iptables", "ip6tables"):
            marker_file = state_file_for(backend)
            try:
                if marker_file.exists():
                    marker_file.unlink()
            except Exception:
                pass

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Restaure un snapshot (menu 7.2) : règles REMPLACÉES entièrement
#   (retrait des règles trackées + application de celles du snapshot),
#   IPs bannies AJOUTÉES uniquement (jamais retirées), jails fail2ban
#   affichées en information seulement.
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration : lecture snapshot + comparaison live + application.
#   Pattern simple, pas de pipeline ExecutionPlan.
#
# Décision de session (asymétrie assumée) :
# - Règles : remplacement sûr car ciblé sur external_ref (jamais un
#   flush système global) — ne touche jamais les règles d'un autre
#   outil (UFW, etc.) jamais trackées par Omega-Fire.
# - IPs : ajout seul car action_2_1_ban_ip n'écrit jamais dans la
#   table bans — aucun moyen fiable de savoir quelles IPs live sont
#   gérées par Omega-Fire, donc un retrait serait dangereux.
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_7_2_restore_state(ctx)
#   ↓ liste les snapshots, résout adapters + rule_repository
# application/commands/restore_state.py : RestoreStateCommand.execute()
#   ↓ _remove_tracked_rules() → _apply_snapshot_rules() → _restore_ips_add_only()
#----------------------------------------------------------------------
