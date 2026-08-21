# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Permission guard for the application pipeline.

This guard verifies that the current user has the required permissions
(typically root) before allowing an action to proceed. It raises
PermissionDeniedError if permissions are insufficient.

The permission check is injectable for testability: by default it uses
os.getuid(), but a custom checker can be provided for testing.
"""
import os
from typing import Callable, Optional
from omega_fire.application.exceptions import PermissionDeniedError


# Type alias for permission checker functions
PermissionChecker = Callable[[], bool]


def _is_root() -> bool:
    """Default permission checker: returns True if running as root.
    
    Returns:
        True if the current user is root (UID 0)
    """
    return os.getuid() == 0


def check_permission(
    requires_root: bool = True,
    checker: Optional[PermissionChecker] = None,
    action_name: str = "unknown",
) -> None:
    """Check if the current user has the required permissions.
    
    This function verifies that the user has sufficient permissions
    to execute the requested action. By default, it checks for root
    access, but a custom checker can be provided.
    
    Args:
        requires_root: Whether root access is required (default: True)
        checker: Optional custom permission checker function.
                 If None, uses the default root check.
        action_name: Name of the action being checked (for error messages)
    
    Raises:
        PermissionDeniedError: If the user lacks required permissions
    """
    if not requires_root:
        return
    
    # Use custom checker if provided, otherwise use default
    check_fn = checker if checker is not None else _is_root
    
    if not check_fn():
        raise PermissionDeniedError(
            required_permission="root",
            reason=f"Action '{action_name}' requires root privileges. "
                   f"Please run with sudo or as root user."
        )


def check_permissions(
    required_permissions: list[str],
    checker: Optional[PermissionChecker] = None,
    action_name: str = "unknown",
) -> None:
    """Check multiple permissions at once.
    
    Currently, the only supported permission is 'root'. This function
    is designed to be extensible for future permission types.
    
    Args:
        required_permissions: List of required permission names
        checker: Optional custom permission checker function
        action_name: Name of the action being checked
    
    Raises:
        PermissionDeniedError: If any required permission is missing
    """
    if "root" in required_permissions:
        check_permission(
            requires_root=True,
            checker=checker,
            action_name=action_name,
        )


def is_permission_granted(
    requires_root: bool = True,
    checker: Optional[PermissionChecker] = None,
) -> bool:
    """Check if permissions are granted without raising an exception.
    
    This is a non-throwing version of check_permission, useful for
    conditional logic where you want to check permissions without
    interrupting the flow.
    
    Args:
        requires_root: Whether root access is required (default: True)
        checker: Optional custom permission checker function
    
    Returns:
        True if permissions are granted, False otherwise
    """
    try:
        check_permission(requires_root=requires_root, checker=checker)
        return True
    except PermissionDeniedError:
        return False


def get_permission_status(
    required_permissions: list[str],
    checker: Optional[PermissionChecker] = None,
) -> dict[str, bool]:
    """Get the status of multiple permissions.
    
    Args:
        required_permissions: List of permission names to check
        checker: Optional custom permission checker function
    
    Returns:
        Dictionary mapping permission name to granted status
    """
    status: dict[str, bool] = {}
    
    for perm in required_permissions:
        if perm == "root":
            check_fn = checker if checker is not None else _is_root
            status[perm] = check_fn()
        else:
            # Unknown permission type — default to False
            status[perm] = False
    
    return status


def get_missing_permissions(
    required_permissions: list[str],
    checker: Optional[PermissionChecker] = None,
) -> list[str]:
    """Get a list of missing permissions.
    
    Args:
        required_permissions: List of permission names to check
        checker: Optional custom permission checker function
    
    Returns:
        List of permission names that are not granted
    """
    status = get_permission_status(required_permissions, checker)
    return [perm for perm, granted in status.items() if not granted]


class PermissionGuard:
    """Stateful permission guard for the pipeline.
    
    This class wraps the permission checking functions and provides
    a consistent interface for the pipeline executor. It can be
    configured with a custom checker for testing.
    """
    
    def __init__(
        self,
        checker: Optional[PermissionChecker] = None,
        skip_checks: bool = False,
    ):
        """Initialize the permission guard.
        
        Args:
            checker: Optional custom permission checker function.
                     If None, uses the default root check.
            skip_checks: If True, all permission checks are skipped.
                         Use only for testing or dry-run mode.
        """
        self._checker = checker
        self._skip_checks = skip_checks
    
    def guard(
        self,
        required_permissions: list[str],
        action_name: str = "unknown",
    ) -> None:
        """Check permissions for an action.
        
        Args:
            required_permissions: List of required permission names
            action_name: Name of the action being checked
        
        Raises:
            PermissionDeniedError: If any required permission is missing
        """
        if self._skip_checks:
            return
        
        check_permissions(
            required_permissions=required_permissions,
            checker=self._checker,
            action_name=action_name,
        )
    
    def is_allowed(
        self,
        required_permissions: list[str],
    ) -> bool:
        """Check if an action is allowed without raising an exception.
        
        Args:
            required_permissions: List of required permission names
        
        Returns:
            True if all permissions are granted
        """
        if self._skip_checks:
            return True
        
        missing = get_missing_permissions(
            required_permissions,
            checker=self._checker,
        )
        return len(missing) == 0
    
    def get_missing(
        self,
        required_permissions: list[str],
    ) -> list[str]:
        """Get missing permissions for an action.
        
        Args:
            required_permissions: List of required permission names
        
        Returns:
            List of missing permission names
        """
        if self._skip_checks:
            return []
        
        return get_missing_permissions(
            required_permissions,
            checker=self._checker,
        )

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Garde de permissions du pipeline. Ce guard vérifie que l'utilisateur dispose des droits nécessaires (typiquement root) pour exécuter une action. Si les permissions sont insuffisantes, il lève PermissionDeniedError. La vérification est injectable pour rester testable sans dépendre du système réel.
# Pourquoi dans application/pipeline/guards/ (charte) :
# - C'est une vérification de workflow avant exécution
# - Lève PermissionDeniedError définie dans application/exceptions.py
# - Ne dépend pas de infrastructure/ (pas de backend, pas de probe)
# - Ne dépend pas de domain/ (pas de logique métier)
# - Testable en injectant une fonction de vérification mockée
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de probe, pas de backend)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis domain/ (pas de logique métier)
# ❌ Pas de subprocess, sqlite3, rich — aucun I/O
# Points clés :
# - check_permission() : vérifie une permission unique (root par défaut), lève PermissionDeniedError
# - check_permissions() : vérifie plusieurs permissions, extensible pour futurs types
# - is_permission_granted() : version non-throwing pour logique conditionnelle
# - get_permission_status() : retourne le statut de chaque permission
# - get_missing_permissions() : retourne la liste des permissions manquantes
# - PermissionGuard : classe stateful pour le pipeline, avec skip_checks pour le dry-run
# - Checker injectable : PermissionChecker = Callable[[], bool] permet de mocker la vérification
# - Aucune dépendance externe : utilise uniquement os (stdlib) et application/exceptions.py
# - Aucun I/O : pas de subprocess, pas de lecture fichier
# Comment il sera utilisé (aperçu) :
# - application/pipeline/executor.py instanciera PermissionGuard et appellera guard() avant chaque step
# - application/commands/ban_ip.py définira requires_permissions=["root"]
# - interfaces/cli/actions.py utilisera is_allowed() pour griser les actions sans permissions
# - Les tests injecteront checker=lambda: True ou checker=lambda: False pour simuler root/non-root
#---------------------------------------------------------------------->
