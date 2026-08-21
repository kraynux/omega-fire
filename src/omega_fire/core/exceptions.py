# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Core exceptions.

Transversal exceptions used across multiple layers of the application.
These exceptions express structural errors related to the core system:
capability registry, audit system, global state. They do not contain
business logic — that belongs in domain/ or application/.
"""


class CoreError(Exception):
    """Base exception for the core layer.
    
    All core-specific exceptions inherit from this class.
    It can be caught to handle any core-level error generically.
    """
    def __init__(self, message: str, context: dict = None):
        """Initialize the core error.
        
        Args:
            message: Human-readable error message
            context: Optional dictionary with additional context
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
    
    def __str__(self) -> str:
        """Return string representation with context.
        
        Returns:
            Error message with context if available
        """
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} [{context_str}]"
        return self.message


class RegistryError(CoreError):
    """Exception raised when the capability registry encounters an error.
    
    This is raised when:
    - A capability cannot be registered or updated
    - The registry is in an inconsistent state
    - A required capability is missing from the registry
    - The registry cannot be initialized properly
    """
    def __init__(
        self,
        message: str,
        capability_id: str = None,
        operation: str = None,
        context: dict = None,
    ):
        """Initialize the registry error.
        
        Args:
            message: Human-readable error message
            capability_id: Optional ID of the capability involved
            operation: Optional name of the operation that failed
            context: Optional dictionary with additional context
        """
        super().__init__(message, context)
        self.capability_id = capability_id
        self.operation = operation
        
        # Enrich context
        if capability_id:
            self.context["capability_id"] = capability_id
        if operation:
            self.context["operation"] = operation


class AuditError(CoreError):
    """Exception raised when the audit system encounters an error.
    
    This is raised when:
    - An audit event cannot be recorded
    - The audit log is corrupted or inaccessible
    - Audit validation fails
    - Audit data cannot be retrieved
    """
    def __init__(
        self,
        message: str,
        event_type: str = None,
        operation: str = None,
        context: dict = None,
    ):
        """Initialize the audit error.
        
        Args:
            message: Human-readable error message
            event_type: Optional type of audit event that failed
            operation: Optional name of the operation that failed
            context: Optional dictionary with additional context
        """
        super().__init__(message, context)
        self.event_type = event_type
        self.operation = operation
        
        # Enrich context
        if event_type:
            self.context["event_type"] = event_type
        if operation:
            self.context["operation"] = operation


class InvalidCapabilityError(RegistryError):
    """Exception raised when a capability is invalid or malformed.
    
    This is raised when:
    - A capability has an invalid ID
    - A capability has an invalid status
    - A capability is missing required fields
    """
    def __init__(
        self,
        message: str,
        capability_id: str = None,
        reason: str = None,
        context: dict = None,
    ):
        """Initialize the invalid capability error.
        
        Args:
            message: Human-readable error message
            capability_id: Optional ID of the invalid capability
            reason: Optional reason why the capability is invalid
            context: Optional dictionary with additional context
        """
        super().__init__(message, capability_id=capability_id, context=context)
        self.reason = reason
        
        if reason:
            self.context["reason"] = reason


class CapabilityNotFoundError(RegistryError):
    """Exception raised when a capability is not found in the registry.
    
    This is raised when:
    - A query references a non-existent capability
    - A guard checks for a capability that was never registered
    """
    def __init__(
        self,
        capability_id: str,
        context: dict = None,
    ):
        """Initialize the capability not found error.
        
        Args:
            capability_id: ID of the missing capability
            context: Optional dictionary with additional context
        """
        message = f"Capability '{capability_id}' not found in registry"
        super().__init__(message, capability_id=capability_id, context=context)


class RegistryStateError(RegistryError):
    """Exception raised when the registry is in an invalid state.
    
    This is raised when:
    - The registry is accessed before initialization
    - The registry is in a corrupted state
    - A state transition is invalid
    """
    def __init__(
        self,
        message: str,
        current_state: str = None,
        expected_state: str = None,
        context: dict = None,
    ):
        """Initialize the registry state error.
        
        Args:
            message: Human-readable error message
            current_state: Optional current state of the registry
            expected_state: Optional expected state
            context: Optional dictionary with additional context
        """
        super().__init__(message, context=context)
        self.current_state = current_state
        self.expected_state = expected_state
        
        if current_state:
            self.context["current_state"] = current_state
        if expected_state:
            self.context["expected_state"] = expected_state

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions transverses de la couche core/. Ces exceptions expriment des erreurs structurelles du système (registre de capacités, audit, état global) et peuvent être levées ou capturées par plusieurs couches. Elles ne contiennent aucune logique métier spécifique — c'est le langage d'erreur commun.
# Pourquoi dans core/ (charte) : 
# - C'est une exception transverse utilisée par plusieurs couches
# - Aucune dépendance externe (pas de domain/, application/, infrastructure/)
# - Testable en mémoire pure
# - Utilisée par core/capability_registry.py et potentiellement par application/
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis domain/, application/, infrastructure/, interfaces/
# ❌ Pas de logique métier spécifique (pas de règles firewall, fail2ban, etc.)
# ❌ Pas de subprocess, sqlite3, rich — aucun I/O
# Points clés :
# - CoreError : exception de base de la couche core, avec message et contexte optionnel
# - RegistryError : erreur liée au registre de capacités (capability_id, operation)
# - AuditError : erreur liée au système d'audit (event_type, operation)
# - InvalidCapabilityError : capacité invalide ou malformée (reason)
# - CapabilityNotFoundError : capacité non trouvée dans le registre
# - RegistryStateError : registre dans un état invalide (current_state, expected_state)
# - Contexte enrichi : chaque exception peut porter un dictionnaire de contexte pour le debugging
# - Aucune dépendance externe : utilise uniquement Exception (built-in)
# - Aucun I/O : ne lit ni n'écrit aucun fichier
# Comment il sera utilisé (aperçu) :
# - core/capability_registry.py lèvera RegistryError, CapabilityNotFoundError, RegistryStateError
# - core/audit.py lèvera AuditError
# - application/pipeline/guards/ capturera ces exceptions et les traduira en erreurs applicatives
# - interfaces/cli/ affichera les messages d'erreur de manière lisible

#---------------------------------------------------------------------->
