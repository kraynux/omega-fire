# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Application layer exceptions.

These exceptions express workflow errors in the application layer:
missing capabilities, permission issues, pipeline failures, rollback errors.
They are NOT domain exceptions (business rules) nor infrastructure exceptions
(technical failures). They are caught by interfaces/ and translated into
user-facing messages.
"""


class ApplicationError(Exception):
    """Base exception for application layer."""
    pass


class CapabilityUnavailableError(ApplicationError):
    """Raised when a required capability is not available.
    
    This is raised by capability_guard when a backend or feature
    is MISSING, DEGRADED, or DISQUALIFIED.
    """
    def __init__(self, capability_id: str, status: str, reason: str = ""):
        self.capability_id = capability_id
        self.status = status
        self.reason = reason
        message = f"Capability '{capability_id}' is {status}"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class UseCaseExecutionError(ApplicationError):
    """Raised when a use case fails during execution.
    
    This is raised by executor when a step fails and cannot be recovered.
    """
    def __init__(self, use_case_name: str, reason: str, step_name: str = ""):
        self.use_case_name = use_case_name
        self.reason = reason
        self.step_name = step_name
        message = f"Use case '{use_case_name}' failed"
        if step_name:
            message += f" at step '{step_name}'"
        message += f": {reason}"
        super().__init__(message)


class PermissionDeniedError(ApplicationError):
    """Raised when the user lacks required permissions.
    
    This is raised by permission_guard when root access is required
    but not available.
    """
    def __init__(self, required_permission: str, reason: str = ""):
        self.required_permission = required_permission
        self.reason = reason
        message = f"Permission denied: {required_permission} required"
        if reason:
            message += f" ({reason})"
        super().__init__(message)


class InvalidRequestError(ApplicationError):
    """Raised when a request object is invalid.
    
    This is raised by use cases when the input parameters fail validation.
    """
    def __init__(self, request_type: str, errors: list[str]):
        self.request_type = request_type
        self.errors = errors
        message = f"Invalid request '{request_type}': {'; '.join(errors)}"
        super().__init__(message)


class RollbackError(ApplicationError):
    """Raised when a rollback operation fails.
    
    This is raised by rollback_guard or executor when attempting to
    undo a failed step.
    """
    def __init__(self, step_name: str, reason: str):
        self.step_name = step_name
        self.reason = reason
        super().__init__(f"Rollback failed for step '{step_name}': {reason}")


class DegradedModeError(ApplicationError):
    """Raised when an action is blocked by degraded mode.
    
    This is raised by degraded_mode when a partial action is not allowed
    or when the system is in a state that prevents execution.
    """
    def __init__(self, action_name: str, reason: str):
        self.action_name = action_name
        self.reason = reason
        super().__init__(f"Action '{action_name}' blocked in degraded mode: {reason}")


class PipelineExecutionError(ApplicationError):
    """Raised when the pipeline encounters an unrecoverable error.
    
    This is a generic error for pipeline-level failures that don't fit
    into more specific categories.
    """
    def __init__(self, pipeline_name: str, reason: str):
        self.pipeline_name = pipeline_name
        self.reason = reason
        super().__init__(f"Pipeline '{pipeline_name}' failed: {reason}")


class StepExecutionError(ApplicationError):
    """Raised when a pipeline step fails.
    
    This is raised by executor when a specific step cannot be executed.
    """
    def __init__(self, step_name: str, reason: str, can_retry: bool = False):
        self.step_name = step_name
        self.reason = reason
        self.can_retry = can_retry
        message = f"Step '{step_name}' failed: {reason}"
        if can_retry:
            message += " (retryable)"
        super().__init__(message)


class HookExecutionError(ApplicationError):
    """Raised when a pipeline hook fails.
    
    This is raised by executor when an audit, metrics, or notification hook fails.
    """
    def __init__(self, hook_name: str, reason: str):
        self.hook_name = hook_name
        self.reason = reason
        super().__init__(f"Hook '{hook_name}' failed: {reason}")


class BackendNotAvailableError(ApplicationError):
    """Raised when a specific backend is not available.
    
    This is a more specific version of CapabilityUnavailableError for
    backend-related operations.
    """
    def __init__(self, backend_name: str, reason: str = ""):
        self.backend_name = backend_name
        self.reason = reason
        message = f"Backend '{backend_name}' is not available"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class PartialExecutionError(ApplicationError):
    """Raised when a multi-step operation partially succeeds.
    
    This is raised by executor when some steps succeed but others fail,
    and the operation cannot be fully rolled back.
    """
    def __init__(self, operation_name: str, succeeded_steps: list[str], failed_steps: list[str]):
        self.operation_name = operation_name
        self.succeeded_steps = succeeded_steps
        self.failed_steps = failed_steps
        message = (
            f"Operation '{operation_name}' partially failed: "
            f"{len(succeeded_steps)} succeeded, {len(failed_steps)} failed"
        )
        super().__init__(message)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions applicatives pour le pipeline et les cas d'usage. Ces exceptions expriment des erreurs de workflow (capacité manquante, permission refusée, rollback échoué), pas des erreurs métier pures (domain/) ni des erreurs techniques (infrastructure/).
# Pourquoi dans application/ (charte) :
# - C'est la couche d'orchestration qui gère les cas d'usage
# - Ces exceptions sont levées par les guards, le planner, l'executor
# - Elles sont capturées par interfaces/ et traduites en messages utilisateur
# - Elles ne dépendent pas de domain/ ni de infrastructure/
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de détails techniques)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis domain/ (pas de logique métier)
# ❌ Pas de subprocess, sqlite3, rich — aucun I/O
# Points clés :
# - CapabilityUnavailableError : levée par capability_guard quand une capacité est manquante
# - UseCaseExecutionError : levée par executor quand un cas d'usage échoue
# - PermissionDeniedError : levée par permission_guard quand les droits sont insuffisants
# - InvalidRequestError : levée par les cas d'usage quand les paramètres sont invalides
# - RollbackError : levée quand le rollback échoue
# - DegradedModeError : levée quand le mode dégradé bloque une action
# - PipelineExecutionError : erreur générique du pipeline
# - StepExecutionError : échec d'un step spécifique
# - HookExecutionError : échec d'un hook (audit, metrics, notification)
# - BackendNotAvailableError : backend spécifique indisponible
# - PartialExecutionError : opération partiellement réussie
# Comment il sera utilisé (aperçu) :
# - application/pipeline/guards/capability_guard.py lèvera CapabilityUnavailableError
# - application/pipeline/guards/permission_guard.py lèvera PermissionDeniedError
# - application/pipeline/executor.py lèvera StepExecutionError, UseCaseExecutionError
# - application/pipeline/rollback.py lèvera RollbackError
# - interfaces/cli/actions.py capturera ces exceptions et les traduira en messages utilisateur
#---------------------------------------------------------------------->
