# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Restore preset state use case.

Orchestrates restoring the firewall to the state it was in just before
the last preset was applied on a given backend (menu 3.4, option [R]):
reloads that backend's own ruleset snapshot, via the backend adapter.
Always wipes the current ruleset before reloading — never cumulates
with whatever the active preset left behind.

Conforms to Omega-Fire architecture charter:
- No direct subprocess calls (delegates entirely to the backend adapter)
- No hardcoded runtime paths (uses infrastructure/config/paths.py)
- Refuses to act if the snapshot cannot be confirmed readable first —
  never flushes the ruleset without a guaranteed way to reload it after
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here
"""
from dataclasses import dataclass
from typing import Any

from omega_fire.application.commands.apply_preset import snapshot_file_for, state_file_for


@dataclass
class RestorePresetStateRequest:
    """Input for the restore preset state use case."""
    backend: str


@dataclass
class RestorePresetStateResult:
    """Output of the restore preset state use case."""
    success: bool
    message: str


class RestorePresetStateCommand:
    """Use case: reload the ruleset snapshot saved before the last preset."""

    def __init__(self, firewall_adapter: Any):
        """Initialize the command.

        Args:
            firewall_adapter: Already-resolved backend adapter (nftables or
                iptables), matching the backend the active preset was
                applied on. Must expose load_ruleset().
        """
        self._adapter = firewall_adapter

    def execute(self, request: RestorePresetStateRequest) -> RestorePresetStateResult:
        if self._adapter is None:
            return RestorePresetStateResult(
                success=False,
                message=f"Aucun backend disponible pour restaurer l'état sur {request.backend}.",
            )

        snapshot_file = snapshot_file_for(request.backend)
        state_file = state_file_for(request.backend)

        # --- Vérification de sécurité : ne jamais flusher sans snapshot lisible ---
        if not snapshot_file.exists():
            return RestorePresetStateResult(
                success=False,
                message=f"Aucun état antérieur disponible pour restauration sur {request.backend}. "
                        f"Rien n'a été modifié. Reconstruisez vos règles via 3.1/3.3 si nécessaire.",
            )

        try:
            snapshot_content = snapshot_file.read_text(encoding="utf-8")
        except Exception as e:
            return RestorePresetStateResult(
                success=False,
                message=f"Impossible de lire la sauvegarde de l'état antérieur ({e}). "
                        f"Rien n'a été modifié.",
            )

        # --- Restauration (flush + reload, jamais de cumul) ---
        try:
            self._adapter.load_ruleset(snapshot_content)
        except Exception as e:
            return RestorePresetStateResult(
                success=False,
                message=f"Échec de la restauration sur {request.backend} : {e}. "
                        f"Le système peut être dans un état incohérent — vérifiez "
                        f"manuellement l'état du pare-feu.",
            )

        # --- Nettoyage : le snapshot de CE backend vient d'être consommé ---
        try:
            if state_file.exists():
                state_file.unlink()
            if snapshot_file.exists():
                snapshot_file.unlink()
        except Exception:
            # Non bloquant : la restauration technique a réussi, seul le
            # nettoyage des marqueurs a échoué.
            pass

        return RestorePresetStateResult(
            success=True,
            message=(
                f"L'état antérieur a été restauré avec succès sur {request.backend}. "
                f"Pensez à repasser par 3.3 (Lister les règles) pour resynchroniser "
                f"la base avec l'état réellement actif dans le noyau."
            ),
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Restaure le ruleset d'un backend donné à l'état qu'il avait juste
#   avant l'application du dernier profil sur CE backend (menu 3.4,
#   option [R]). Recharge le snapshot propre à ce backend, sauvegardé
#   par ApplyPresetCommand.
# - Flush systématique avant rechargement : jamais de cumul entre le
#   profil actif et l'état restauré.
#
# Pourquoi dans application/commands/ (charte) :
# - Cas d'usage qui orchestre lecture snapshot + restauration + nettoyage.
# - Ne fait aucun subprocess direct (délégué à l'adapter).
# - Ne code aucun chemin en dur (réutilise snapshot_file_for()/
#   state_file_for() de apply_preset.py).
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (adapter reçu en paramètre)
# ❌ Pas de rendu UI
#
# Points clés :
# - Fichiers NAMESPACÉS par backend (voir apply_preset.py) : restaurer
#   nftables ne touche jamais à l'état/snapshot d'iptables et vice-versa —
#   les deux backends peuvent être testés indépendamment sans écrasement
#   croisé.
# - Sécurité : si le snapshot du backend concerné est absent ou illisible,
#   AUCUNE action destructrice n'est tentée (pas de flush) — le pare-feu
#   reste inchangé plutôt que vidé sans pouvoir être rechargé
# - Après restauration réussie : suppression du snapshot/état de CE
#   backend uniquement (un seul snapshot par backend à la fois, consommé
#   une fois restauré)
# - IMPORTANT (nftables) : les handles des règles managed peuvent changer
#   après un flush+reload, ce qui rend leur external_ref potentiellement
#   obsolète en base — d'où la recommandation de repasser par 3.3
#   (SyncRulesFromBackendsCommand) pour resynchroniser après restauration
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_3_4_apply_preset(ctx), option [R]
#   ↓ résout l'adapter via ctx.container.get_firewall_port(backend)
# application/commands/restore_preset_state.py : RestorePresetStateCommand.execute()
#   ↓ adapter.load_ruleset()
#---------------------------------------------------------------------->
