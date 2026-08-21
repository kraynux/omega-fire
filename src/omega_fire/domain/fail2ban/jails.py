# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban jails validation logic.

Pure domain logic for validating fail2ban jails.
This module defines WHAT makes a jail valid, not HOW it is created
or managed by fail2ban-client.
"""
import re
from typing import Optional
from omega_fire.domain.fail2ban.models import Jail, JailConfig, JailStatus, JailManagedBy
from omega_fire.domain.fail2ban.exceptions import (
    InvalidJailConfigError,
    InvalidParameterError,
)


def validate_jail_name(name: str) -> bool:
    """Validate a jail name according to fail2ban conventions.
    
    Rules:
    - Must be non-empty
    - Must contain only alphanumeric characters, hyphens, underscores
    - Must not start with a digit
    - Maximum length: 64 characters
    
    Args:
        name: Jail name to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False
    
    if len(name) > 64:
        return False
    
    # Must start with a letter
    if name[0].isdigit():
        return False
    
    # Only alphanumeric, hyphens, underscores
    pattern = r'^[a-zA-Z][a-zA-Z0-9_-]*$'
    return bool(re.match(pattern, name))


def validate_maxretry(value: int) -> None:
    """Validate the maxretry parameter.
    
    Rules:
    - Must be >= 1
    
    Args:
        value: maxretry value to validate
    
    Raises:
        InvalidParameterError: If value is invalid
    """
    if value < 1:
        raise InvalidParameterError(
            "maxretry",
            value,
            "maxretry must be >= 1"
        )


def validate_bantime(value: int) -> None:
    """Validate the bantime parameter.
    
    Rules:
    - Must be >= 0 (0 means permanent ban)
    
    Args:
        value: bantime value to validate (in seconds)
    
    Raises:
        InvalidParameterError: If value is invalid
    """
    if value < 0:
        raise InvalidParameterError(
            "bantime",
            value,
            "bantime must be >= 0 (0 = permanent ban)"
        )


def validate_findtime(value: int) -> None:
    """Validate the findtime parameter.
    
    Rules:
    - Must be >= 0
    
    Args:
        value: findtime value to validate (in seconds)
    
    Raises:
        InvalidParameterError: If value is invalid
    """
    if value < 0:
        raise InvalidParameterError(
            "findtime",
            value,
            "findtime must be >= 0"
        )


def validate_jail_config(config: JailConfig) -> list[str]:
    """Validate a complete jail configuration.
    
    Args:
        config: JailConfig to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    return config.validate()


def validate_jail(jail: Jail) -> list[str]:
    """Validate a complete jail (config + state).
    
    Args:
        jail: Jail to validate
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = validate_jail_config(jail.config)
    
    # Additional jail-level validations
    if not validate_jail_name(jail.name):
        errors.append(f"Invalid jail name: '{jail.name}'")
    
    if jail.name != jail.config.jail_name:
        errors.append(f"Jail name mismatch: jail.name='{jail.name}' vs config.jail_name='{jail.config.jail_name}'")
    
    return errors


def create_valid_jail_config(
    jail_name: str,
    log_path: str,
    maxretry: int = 5,
    bantime: int = 3600,
    findtime: int = 600,
    backend: str = "nftables",
    filter_name: Optional[str] = None,
    port: Optional[str] = None,
    protocol: Optional[str] = None,
    action: Optional[str] = None,
    enabled: bool = True,
) -> JailConfig:
    """Create a validated JailConfig.
    
    This function validates all parameters before creating the config.
    
    Args:
        jail_name: Name of the jail
        log_path: Path to the log file to monitor
        maxretry: Number of failures before ban (default: 5)
        bantime: Ban duration in seconds (default: 3600, 0 = permanent)
        findtime: Time window for counting failures (default: 600)
        backend: Backend used by this jail (default: 'nftables')
        filter_name: Fail2ban filter name (optional)
        port: Port(s) to monitor (optional, e.g., "80", "80,443")
        protocol: Protocol (optional, e.g., "tcp", "udp")
        action: Fail2ban action name (optional)
        enabled: Whether the jail is enabled (default: True)
    
    Returns:
        Validated JailConfig
    
    Raises:
        InvalidJailConfigError: If the jail name is invalid
        InvalidParameterError: If any parameter is invalid
    """
    # Validate jail name
    if not validate_jail_name(jail_name):
        raise InvalidJailConfigError(
            jail_name,
            f"Invalid jail name: '{jail_name}'"
        )
    
    # Validate parameters
    validate_maxretry(maxretry)
    validate_bantime(bantime)
    validate_findtime(findtime)
    
    # Create config
    config = JailConfig(
        jail_name=jail_name,
        backend=backend,
        log_path=log_path,
        filter_name=filter_name,
        maxretry=maxretry,
        bantime=bantime,
        findtime=findtime,
        port=port,
        protocol=protocol,
        action=action,
        enabled=enabled,
    )
    
    # Final validation
    errors = config.validate()
    if errors:
        raise InvalidJailConfigError(jail_name, "; ".join(errors))
    
    return config


def create_valid_jail(
    jail_name: str,
    log_path: str,
    maxretry: int = 5,
    bantime: int = 3600,
    findtime: int = 600,
    backend: str = "nftables",
    filter_name: Optional[str] = None,
    port: Optional[str] = None,
    protocol: Optional[str] = None,
    action: Optional[str] = None,
    enabled: bool = True,
    managed_by: JailManagedBy = JailManagedBy.EXTERNAL,
) -> Jail:
    """Create a validated Jail.
    
    This function validates all parameters before creating the jail.
    
    Args:
        jail_name: Name of the jail
        log_path: Path to the log file to monitor
        maxretry: Number of failures before ban (default: 5)
        bantime: Ban duration in seconds (default: 3600, 0 = permanent)
        findtime: Time window for counting failures (default: 600)
        backend: Backend used by this jail (default: 'nftables')
        filter_name: Fail2ban filter name (optional)
        port: Port(s) to monitor (optional)
        protocol: Protocol (optional)
        action: Fail2ban action name (optional)
        enabled: Whether the jail is enabled (default: True)
        managed_by: Who manages this jail (default: EXTERNAL)
    
    Returns:
        Validated Jail
    
    Raises:
        InvalidJailConfigError: If the jail name is invalid
        InvalidParameterError: If any parameter is invalid
    """
    config = create_valid_jail_config(
        jail_name=jail_name,
        log_path=log_path,
        maxretry=maxretry,
        bantime=bantime,
        findtime=findtime,
        backend=backend,
        filter_name=filter_name,
        port=port,
        protocol=protocol,
        action=action,
        enabled=enabled,
    )
    
    jail = Jail(
        name=jail_name,
        config=config,
        status=JailStatus.ACTIVE if enabled else JailStatus.DISABLED,
        managed_by=managed_by,
    )
    
    return jail

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les règles de validation pour les jails fail2ban. Ce module valide les noms de jails, les paramètres de configuration (maxretry, bantime, findtime), et fournit des fonctions pour créer des jails valides.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : qu'est-ce qu'un jail valide, quels paramètres sont acceptables
# - Aucune dépendance externe (utilise uniquement les modèles du domaine)
# - Fonctions pures : pas d'effet de bord, testable en mémoire
# - Utilisé par domain/fail2ban/service.py pour valider les jails avant création
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/ (pas d'appel à fail2ban-client)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de logique d'exécution (juste la validation)
# Points clés :
# - Validation stricte : vérifie les noms de jails, maxretry, bantime, findtime
# - Fonctions pures : aucune modification d'état, juste de la validation
# - Exceptions métier : lève InvalidJailConfigError et InvalidParameterError
# - create_valid_jail_config() : crée une config validée en une seule étape
# - create_valid_jail() : crée un jail complet validé
# - Aucune dépendance externe : utilise uniquement les modèles du domaine
# Comment il sera utilisé (aperçu) :
# - domain/fail2ban/service.py appellera create_valid_jail() pour créer des jails valides
# - application/commands/jail_ban.py utilisera ces validations avant de bannir une IP
# - interfaces/cli/actions.py proposera les paramètres à l'utilisateur, puis le service validera
#---------------------------------------------------------------------->
