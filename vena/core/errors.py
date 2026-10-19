"""Error hierarchy for the Vena agent.

Every error carries a machine-readable class so callers can branch on failure
type (e.g. PermissionDenied vs ValidationError) instead of parsing strings.
"""


class VenaError(Exception):
    """Base class for all Vena errors."""


class ConfigError(VenaError):
    pass


class BodyTooLarge(VenaError):
    """Request body exceeded the endpoint's size limit (HTTP 413)."""


class ProviderError(VenaError):
    pass


class ProviderUnavailable(ProviderError):
    pass


class ProviderAuthError(ProviderError):
    pass


class MemoryError(VenaError):
    pass


class ToolError(VenaError):
    pass


class PermissionDenied(ToolError):
    pass


class ValidationError(ToolError):
    pass


class PlannerError(VenaError):
    pass


class Cancelled(PlannerError):
    pass


class BudgetExceeded(PlannerError):
    pass
