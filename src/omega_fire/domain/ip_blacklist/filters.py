# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)

"""IP blacklist filtering logic.

Pure functions for filtering ban entries by various criteria.
These functions do not modify the original entries — they return
new filtered lists.
"""
from datetime import datetime
from typing import Optional
from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus, IPList


def filter_by_status(entries: list[BanEntry], status: BanStatus) -> list[BanEntry]:
    """Filter entries by their lifecycle status.
    
    Args:
        entries: List of ban entries to filter
        status: Target status (ACTIVE, EXPIRED, REMOVED)
    
    Returns:
        New list containing only entries with the specified status
    """
    return [e for e in entries if e.status == status]


def filter_by_backend(entries: list[BanEntry], backend: str) -> list[BanEntry]:
    """Filter entries by backend label.
    
    Args:
        entries: List of ban entries to filter
        backend: Backend name ('nftables', 'iptables', 'fail2ban')
    
    Returns:
        New list containing only entries from the specified backend
    """
    return [e for e in entries if e.backend == backend]


def filter_by_date_range(
    entries: list[BanEntry],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> list[BanEntry]:
    """Filter entries by ban date range.
    
    Args:
        entries: List of ban entries to filter
        start_date: Minimum ban date (inclusive). None = no lower bound
        end_date: Maximum ban date (inclusive). None = no upper bound
    
    Returns:
        New list containing only entries banned within the date range
    """
    filtered = entries
    if start_date:
        filtered = [e for e in filtered if e.banned_at >= start_date]
    if end_date:
        filtered = [e for e in filtered if e.banned_at <= end_date]
    return filtered


def filter_active_only(entries: list[BanEntry]) -> list[BanEntry]:
    """Filter to keep only currently active bans.
    
    A ban is active if its status is ACTIVE and it has not expired.
    
    Args:
        entries: List of ban entries to filter
    
    Returns:
        New list containing only active bans
    """
    return [e for e in entries if e.is_active()]


def filter_by_ip(entries: list[BanEntry], ip: str) -> list[BanEntry]:
    """Filter entries by IP address.
    
    Args:
        entries: List of ban entries to filter
        ip: Target IP address
    
    Returns:
        New list containing only entries for the specified IP
    """
    return [e for e in entries if e.ip == ip]


def filter_by_jail(entries: list[BanEntry], jail_name: str) -> list[BanEntry]:
    """Filter entries by fail2ban jail name.
    
    Args:
        entries: List of ban entries to filter
        jail_name: Target jail name
    
    Returns:
        New list containing only entries from the specified jail
    """
    return [e for e in entries if e.jail_name == jail_name]


def filter_by_source(entries: list[BanEntry], source: str) -> list[BanEntry]:
    """Filter entries by ban source.
    
    Args:
        entries: List of ban entries to filter
        source: Source type ('manual', 'sync', 'import', 'fail2ban_transfer')
    
    Returns:
        New list containing only entries from the specified source
    """
    from omega_fire.domain.ip_blacklist.models import BanSource
    try:
        source_enum = BanSource(source)
        return [e for e in entries if e.source == source_enum]
    except ValueError:
        return []


def combine_filters(
    entries: list[BanEntry],
    status: Optional[BanStatus] = None,
    backend: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    ip: Optional[str] = None,
    jail_name: Optional[str] = None,
    source: Optional[str] = None
) -> list[BanEntry]:
    """Apply multiple filters in sequence.
    
    This is a convenience function that chains multiple filter criteria.
    All specified filters are applied (AND logic).
    
    Args:
        entries: List of ban entries to filter
        status: Filter by status (optional)
        backend: Filter by backend (optional)
        start_date: Filter by minimum ban date (optional)
        end_date: Filter by maximum ban date (optional)
        ip: Filter by IP address (optional)
        jail_name: Filter by jail name (optional)
        source: Filter by source (optional)
    
    Returns:
        New list containing only entries matching all specified criteria
    """
    result = entries
    
    if status is not None:
        result = filter_by_status(result, status)
    if backend is not None:
        result = filter_by_backend(result, backend)
    if start_date is not None or end_date is not None:
        result = filter_by_date_range(result, start_date, end_date)
    if ip is not None:
        result = filter_by_ip(result, ip)
    if jail_name is not None:
        result = filter_by_jail(result, jail_name)
    if source is not None:
        result = filter_by_source(result, source)
    
    return result
    
# <-- INFO DEV ---------------------------------------------------------
# Rôle : 
# - Fonctions de filtrage pur sur les collections de BanEntry. Ces fonctions appliquent des critères métier (statut, backend, date, IP) sans modifier les données originales — elles retournent de nouvelles listes.
# Pourquoi dans domain/ : 
# - C'est de la logique métier : comment filtrer une blacklist selon des critères fonctionnels
# - Aucune dépendance externe (opère sur les modèles du domaine)
# - Fonctions pures : pas d'effet de bord, testable en mémoire
# - Utilisé par application/queries/list_banned_ips.py pour construire les réponses
# ❌ Ce qu'il ne contient PAS (règles projet)
# ❌ Pas d'import depuis infrastructure/ (pas de requête SQL)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas de modification des BanEntry originaux (immutable par convention)
# Points clés :
# - Fonctions pures : aucune modification des données originales, retour de nouvelles listes
# - Composition : combine_filters() permet d'appliquer plusieurs critères en chaîne (AND logique)
# - Typage strict : tous les paramètres et retours sont typés pour la vérification statique
# - Aucune dépendance externe : opère uniquement sur les modèles du domaine
# - Testable en mémoire : peut être testé avec des BanEntry construits manuellement
# Comment il sera utilisé (aperçu) : 
# - application/queries/list_banned_ips.py utilisera ces filtres pour construire les réponses
# - interfaces/cli/actions.py passera les critères utilisateur à combine_filters()
# - domain/ip_blacklist/service.py pourra utiliser ces filtres pour des opérations métier
#---------------------------------------------------------------------->
