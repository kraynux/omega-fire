# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Logique de rotation des snapshots.

Détermine quels snapshots doivent être supprimés pour respecter la
limite de conservation des snapshots automatiques (AUTO_PRESET),
sans jamais affecter les snapshots manuels (MANUAL, conservation
illimitée).

Fonctions pures : aucun I/O, aucune dépendance à SQLite ou au système
de fichiers. L'exécution réelle (suppression fichier + ligne DB) est
déléguée à application/.
"""
from __future__ import annotations

from omega_fire.domain.persistence.snapshots import Snapshot, SnapshotOrigin

DEFAULT_MAX_AUTO_SNAPSHOTS = 5


def compute_snapshots_to_delete(
    snapshots: list[Snapshot],
    max_auto_snapshots: int = DEFAULT_MAX_AUTO_SNAPSHOTS,
) -> list[Snapshot]:
    """Calcule les snapshots automatiques à supprimer pour respecter la limite.

    Les snapshots MANUAL ne sont jamais retournés, quel que soit leur
    nombre ou leur ancienneté.

    Args:
        snapshots: liste complète des snapshots existants (tous origins).
        max_auto_snapshots: nombre maximum de snapshots AUTO_PRESET à
            conserver. Au-delà, les plus anciens sont retournés pour
            suppression.

    Returns:
        Liste des snapshots AUTO_PRESET excédentaires, triés du plus
        ancien au plus récent (ordre de suppression recommandé).
    """
    auto_snapshots = [
        s for s in snapshots
        if s.metadata.origin == SnapshotOrigin.AUTO_PRESET
    ]

    if len(auto_snapshots) <= max_auto_snapshots:
        return []

    auto_snapshots_sorted = sorted(
        auto_snapshots, key=lambda s: s.metadata.created_at
    )

    excess_count = len(auto_snapshots_sorted) - max_auto_snapshots
    return auto_snapshots_sorted[:excess_count]


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Calcule quels snapshots AUTO_PRESET doivent être supprimés pour
#   respecter la limite de conservation (5 par défaut).
# - Ignore totalement les snapshots MANUAL (conservation illimitée,
#   décision actée en session).
#
# Pourquoi dans domain/ (charte) :
# - Règle métier pure : quand et combien de snapshots conserver.
# - Dépend uniquement de domain/persistence/snapshots.py (même sous-domaine),
#   jamais de core/, ports/, infrastructure/, application/ ou interfaces/.
# - Fonction pure : pas d'I/O, testable avec des objets Snapshot en mémoire.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'accès SQLite (c'est infrastructure/storage/)
# ❌ Pas de suppression de fichier (c'est infrastructure/)
# ❌ Pas d'import depuis core/ ou ports/ (domain/ ne dépend d'aucune autre couche)
#
# Points clés :
# - compute_snapshots_to_delete() : point d'entrée unique, pur.
# - DEFAULT_MAX_AUTO_SNAPSHOTS = 5 (décision de session).
# - Opère sur Snapshot.metadata.origin / Snapshot.metadata.created_at
#   (structure réelle définie dans domain/persistence/snapshots.py).
# - S'inspire de compute_rotations_to_delete() dans domain/logs/rotation.py.
#
# Comment il sera utilisé (aperçu) :
# - domain/persistence/service.py (ou application/commands/apply_preset.py)
#   appellera cette fonction après chaque création d'un snapshot
#   AUTO_PRESET, pour savoir quoi supprimer, puis délèguera la
#   suppression réelle au PersistencePort.
#----------------------------------------------------------------------
