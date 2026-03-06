class BackendError(RuntimeError):
    """Base class for backend-related errors."""
    pass


class BackendNotFoundError(BackendError):
    """Raised when a backend name cannot be resolved from the registry."""
    pass


class BackendConfigError(BackendError):
    """Raised when backend configuration (env vars, args) is invalid or missing."""
    pass


class BackendRequestError(BackendError):
    """Raised when a backend request fails (HTTP error, timeout, bad response)."""
    pass