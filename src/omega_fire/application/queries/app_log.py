# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Query: Read application log.

Provides read-only access to the application log file.
Used by menus 1.5 (journal applicatif) and 7.3 (historique actions).

Conforms to Omega-Fire architecture charter:
- Read-only query, no side effects
- Consumes ports/audit.py contract (not infrastructure directly)
- Returns formatted string for UI display
- No dependency on interfaces/ or infrastructure/ directly
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional


# ----------------------------------------------------------------------
# Default log paths (fallback if port not available)
# ----------------------------------------------------------------------
DEFAULT_LOG_PATHS = [
    Path("var/logs/app.log"),
    Path("/var/log/omega-fire/app.log"),
    Path("/var/log/omega-fire.log"),
]

def read_app_log(
    audit_port: Optional[Any] = None,
    max_lines: int = 100,
    keyword: str = "",
) -> str:
    """1.5 / 7.3: Read the application log file."""
    # Try to use the port if available
    if audit_port is not None:
        try:
            entries = []
            if hasattr(audit_port, 'get_recent'):
                entries = audit_port.get_recent(limit=max_lines)
            elif hasattr(audit_port, 'read_log'):
                entries = audit_port.read_log(max_lines=max_lines, keyword=keyword)
            
            if entries:
                return _format_log_entries(entries, keyword)
        except Exception as e:
            return f"⚠️ Erreur lors de la lecture via le port : {e}\n\n" + _fallback_read(max_lines, keyword)

    # Fallback: direct file reading (temporary until port is fully wired)
    return _fallback_read(max_lines, keyword)


def _format_log_entries(entries: list, keyword: str) -> str:
    """Format log entries from AuditPort without hardcoded colors."""
    header = "📋 Journal applicatif\n═══════════════════════\n\n"
    if keyword:
        header += f"Filtre : '{keyword}'\n\n"

    # Filtrage par mot-clé si nécessaire
    if keyword:
        kw = keyword.lower()
        filtered = []
        for e in entries:
            act = getattr(e, 'action', str(e)).lower()
            actor = getattr(e, 'actor', '').lower()
            target = getattr(e, 'target', '').lower()
            if kw in act or kw in actor or kw in target:
                filtered.append(e)
        entries = filtered

    content = []
    for entry in entries:
        ts = getattr(entry, 'timestamp', '')
        if hasattr(ts, 'strftime'):
            ts = ts.strftime("%Y-%m-%d %H:%M:%S")

        action = getattr(entry, 'action', str(entry))
        actor = getattr(entry, 'actor', 'system')
        target = getattr(entry, 'target', 'N/A')
        success = getattr(entry, 'success', True)
        status_text = "OK" if success else "ÉCHEC"

        content.append(f"[{ts}] [{status_text}] {action} (acteur: {actor}, cible: {target})")

    if not content:
        return header + "Aucune entrée d'audit trouvée."

    return header + "\n".join(content) + f"\n\n({len(content)} entrée(s))"


def _fallback_read(max_lines: int, keyword: str) -> str:
    """Fallback: read log file directly if no audit port data is available."""
    log_path = _find_log_file()
    
    if log_path is None or not log_path.exists():
        return (
            "📋 Journal applicatif\n"
            "═══════════════════════\n\n"
            "ℹ️ Aucun journal d'audit ou fichier de log enregistré pour le moment.\n"
            "Les événements s'afficheront ici au fur et à mesure des actions exécutées (ex: ban, sync, rescan).\n\n"
            "Chemins vérifiés :\n"
            + "\n".join(f"  • {p}" for p in DEFAULT_LOG_PATHS)
        )
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if keyword:
            keyword_lower = keyword.lower()
            lines = [l for l in lines if keyword_lower in l.lower()]
        
        lines = lines[-max_lines:]
        
        if not lines:
            if keyword:
                return f"🔍 Aucune entrée trouvée pour '{keyword}' dans {log_path.name}."
            return f"📋 Le journal {log_path.name} est vide."
        
        return _format_raw_lines(lines, log_path.name, keyword)
    
    except PermissionError:
        return f"❌ Permission refusée pour lire {log_path}.\nEssayez avec sudo ou vérifiez les permissions."
    except Exception as e:
        return f"❌ Erreur lors de la lecture de {log_path} : {e}"



def _find_log_file() -> Optional[Path]:
    """Find the first existing log file from default paths."""
    for path in DEFAULT_LOG_PATHS:
        if path.exists():
            return path
    return None


def _format_log_entries(entries: list, keyword: str) -> str:
    """Format log entries from AuditPort."""
    header = "📋 Journal applicatif\n═══════════════════════\n\n"
    if keyword:
        header += f"Filtre : '{keyword}'\n\n"
    
    content = []
    for entry in entries:
        if hasattr(entry, 'timestamp'):
            ts = entry.timestamp
        elif isinstance(entry, dict):
            ts = entry.get('timestamp', '')
        else:
            ts = ''
        
        if hasattr(entry, 'message'):
            msg = entry.message
        elif isinstance(entry, dict):
            msg = entry.get('message', str(entry))
        else:
            msg = str(entry)
        
        if hasattr(entry, 'level'):
            level = entry.level
        elif isinstance(entry, dict):
            level = entry.get('level', 'INFO')
        else:
            level = 'INFO'
        
        content.append(f"[{ts}] [{level}] {msg}")
    
    return header + "\n".join(content) + f"\n\n({len(content)} entrée(s))"


def _format_raw_lines(lines: list, filename: str, keyword: str) -> str:
    """Format raw log lines from file."""
    header = f"📋 Journal applicatif : {filename}\n"
    header += "═" * 40 + "\n\n"
    if keyword:
        header += f"Filtre : '{keyword}'\n\n"
    
    content = []
    for line in lines:
        line = line.rstrip('\n')
        if line:
            content.append(line)
    
    return header + "\n".join(content) + f"\n\n({len(content)} ligne(s))"


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Query read-only pour lire le journal applicatif.
# - Utilisée par les menus 1.5 (journal) et 7.3 (historique actions).
# - Consomme le port AuditPort si disponible, sinon fallback sur lecture directe.
#
# Pourquoi dans application/queries/ (charte) :
# - C'est une query (lecture seule), pas une command (modification).
# - Retourne une string formatée pour l'interface.
# - Ne dépend pas directement de infrastructure/.
# - Utilise un port (AuditPort) pour l'accès au log.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de modification du fichier de log.
# ❌ Pas d'import direct de infrastructure/logging/.
# ❌ Pas de logique métier (c'est le rôle de domain/).
# ❌ Pas de rendu UI (c'est le rôle de interfaces/).
#
# Points clés :
# - read_app_log() : fonction principale avec audit_port optionnel.
# - _fallback_read() : lecture directe temporaire (à remplacer par port).
# - _find_log_file() : cherche le premier fichier de log existant.
# - _format_log_entries() : formatage depuis AuditPort.
# - _format_raw_lines() : formatage depuis lecture directe.
# - DEFAULT_LOG_PATHS : chemins par défaut (var/logs/, /var/log/).
# - Support du filtrage par mot-clé (keyword).
# - Support de la limitation (max_lines).
#
# TODO :
# - Remplacer le fallback par l'implémentation complète de AuditPort.
# - Ajouter la pagination pour les gros fichiers de log.
# - Ajouter le support de la recherche avancée (regex, date).
#---------------------------------------------------------------------->
