# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban parameter validation logic.

Pure domain logic for validating fail2ban-specific parameters.
This module complements jails.py by validating ports, log paths,
filter names, protocols, and actions.
"""
import os
import re
from typing import Optional
from omega_fire.domain.fail2ban.exceptions import InvalidParameterError


def validate_port(port: str) -> None:
    """Validate a port specification.
    
    Rules:
    - Can be a single port: "80"
    - Can be a comma-separated list: "80,443"
    - Can be a range: "8000-9000"
    - Can be a service name: "http", "https", "ssh"
    - Can mix formats: "80,443,8000-9000,http"
    
    Args:
        port: Port specification to validate
    
    Raises:
        InvalidParameterError: If port format is invalid
    """
    if not port:
        return  # Port is optional
    
    # Split by comma
    parts = port.split(",")
    
    for part in parts:
        part = part.strip()
        
        # Check if it's a range
        if "-" in part:
            range_parts = part.split("-")
            if len(range_parts) != 2:
                raise InvalidParameterError(
                    "port",
                    port,
                    f"Invalid port range format: '{part}'"
                )
            try:
                start, end = int(range_parts[0]), int(range_parts[1])
                if start > end:
                    raise InvalidParameterError(
                        "port",
                        port,
                        f"Port range start ({start}) > end ({end})"
                    )
                if not (1 <= start <= 65535 and 1 <= end <= 65535):
                    raise InvalidParameterError(
                        "port",
                        port,
                        f"Port values must be between 1 and 65535"
                    )
            except ValueError:
                raise InvalidParameterError(
                    "port",
                    port,
                    f"Port range must contain integers: '{part}'"
                )
        
        # Check if it's a number
        elif part.isdigit():
            port_num = int(part)
            if not (1 <= port_num <= 65535):
                raise InvalidParameterError(
                    "port",
                    port,
                    f"Port number must be between 1 and 65535: {port_num}"
                )
        
        # Check if it's a valid service name (alphanumeric)
        elif re.match(r'^[a-zA-Z][a-zA-Z0-9-]*$', part):
            pass  # Valid service name
        
        else:
            raise InvalidParameterError(
                "port",
                port,
                f"Invalid port format: '{part}'"
            )


def validate_log_path(log_path: str) -> None:
    """Validate a log file path format.
    
    Rules:
    - Must be non-empty
    - Must be an absolute path (starts with /)
    - Must not contain invalid characters
    - Note: Does NOT check if file exists (that's infrastructure's job)
    
    Args:
        log_path: Log path to validate
    
    Raises:
        InvalidParameterError: If log path format is invalid
    """
    if not log_path:
        raise InvalidParameterError(
            "log_path",
            log_path,
            "log_path is required"
        )
    
    if not os.path.isabs(log_path):
        raise InvalidParameterError(
            "log_path",
            log_path,
            "log_path must be an absolute path"
        )
    
    # Check for invalid characters
    if "\x00" in log_path:
        raise InvalidParameterError(
            "log_path",
            log_path,
            "log_path contains null bytes"
        )


def validate_filter_name(filter_name: str) -> None:
    """Validate a fail2ban filter name.
    
    Rules:
    - Must be non-empty if provided
    - Must contain only alphanumeric characters, hyphens, underscores
    - Maximum length: 64 characters
    
    Args:
        filter_name: Filter name to validate
    
    Raises:
        InvalidParameterError: If filter name format is invalid
    """
    if not filter_name:
        return  # Filter name is optional
    
    if len(filter_name) > 64:
        raise InvalidParameterError(
            "filter_name",
            filter_name,
            "filter_name must be <= 64 characters"
        )
    
    pattern = r'^[a-zA-Z][a-zA-Z0-9_-]*$'
    if not re.match(pattern, filter_name):
        raise InvalidParameterError(
            "filter_name",
            filter_name,
            "filter_name must start with a letter and contain only alphanumeric, hyphens, underscores"
        )


def validate_protocol(protocol: str) -> None:
    """Validate a protocol specification.
    
    Rules:
    - Must be one of: tcp, udp, tcp,udp (or variations)
    - Case-insensitive
    
    Args:
        protocol: Protocol to validate
    
    Raises:
        InvalidParameterError: If protocol is invalid
    """
    if not protocol:
        return  # Protocol is optional
    
    # Normalize to lowercase
    protocol_lower = protocol.lower().strip()
    
    # Split by comma
    parts = [p.strip() for p in protocol_lower.split(",")]
    
    valid_protocols = {"tcp", "udp"}
    
    for part in parts:
        if part not in valid_protocols:
            raise InvalidParameterError(
                "protocol",
                protocol,
                f"Invalid protocol: '{part}'. Must be tcp, udp, or tcp,udp"
            )


def validate_action(action: str) -> None:
    """Validate a fail2ban action name.
    
    Rules:
    - Must be non-empty if provided
    - Must contain only alphanumeric characters, hyphens, underscores
    - Maximum length: 64 characters
    
    Args:
        action: Action name to validate
    
    Raises:
        InvalidParameterError: If action name format is invalid
    """
    if not action:
        return  # Action is optional
    
    if len(action) > 64:
        raise InvalidParameterError(
            "action",
            action,
            "action must be <= 64 characters"
        )
    
    pattern = r'^[a-zA-Z][a-zA-Z0-9_-]*$'
    if not re.match(pattern, action):
        raise InvalidParameterError(
            "action",
            action,
            "action must start with a letter and contain only alphanumeric, hyphens, underscores"
        )


def validate_all_parameters(
    port: Optional[str] = None,
    log_path: Optional[str] = None,
    filter_name: Optional[str] = None,
    protocol: Optional[str] = None,
    action: Optional[str] = None,
) -> list[str]:
    """Validate all optional fail2ban parameters.
    
    Args:
        port: Port specification (optional)
        log_path: Log file path (optional)
        filter_name: Filter name (optional)
        protocol: Protocol (optional)
        action: Action name (optional)
    
    Returns:
        List of validation error messages (empty if all valid)
    """
    errors = []
    
    try:
        if port is not None:
            validate_port(port)
    except InvalidParameterError as e:
        errors.append(str(e))
    
    try:
        if log_path is not None:
            validate_log_path(log_path)
    except InvalidParameterError as e:
        errors.append(str(e))
    
    try:
        if filter_name is not None:
            validate_filter_name(filter_name)
    except InvalidParameterError as e:
        errors.append(str(e))
    
    try:
        if protocol is not None:
            validate_protocol(protocol)
    except InvalidParameterError as e:
        errors.append(str(e))
    
    try:
        if action is not None:
            validate_action(action)
    except InvalidParameterError as e:
        errors.append(str(e))
    
    return errors

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les règles de validation complémentaires pour les paramètres fail2ban : ports, chemins de logs, noms de filtres, protocoles, actions. Ce module complète jails.py qui valide les paramètres numériques (maxretry, bantime, findtime).
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : qu'est-ce qu'un paramètre fail2ban valide
# - Aucune dépendance externe (juste re, os.path)
# - Fonctions pures : pas d'effet de bord, testable en mémoire
# - Utilisé par domain/fail2ban/service.py pour valider les configurations
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/ (pas d'accès au système de fichiers)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de vérification que les fichiers existent (juste validation de format)
# Points clés :
# Validation de format : vérifie le format des paramètres, pas leur existence sur le système
# - 5 fonctions de validation :
#   - validate_port() : accepte "80", "80,443", "8000-9000", "http", ou mélange
#   - validate_log_path() : vérifie que c'est un chemin absolu
#   - validate_filter_name() : valide le format du nom de filtre
#   - validate_protocol() : accepte "tcp", "udp", "tcp,udp"
#   - validate_action() : valide le format du nom d'action
# - validate_all_parameters() : valide tous les paramètres en une seule passe
# - Aucune dépendance externe : utilise uniquement re et os.path de la stdlib
# - Testable en mémoire : ne vérifie pas si les fichiers existent
# Comment il sera utilisé (aperçu) :
# - domain/fail2ban/service.py appellera ces validations avant de créer un jail
# - domain/fail2ban/jails.py pourrait utiliser validate_all_parameters() dans create_valid_jail_config()
# - interfaces/cli/actions.py validera les entrées utilisateur avant de les passer au service
#---------------------------------------------------------------------->
