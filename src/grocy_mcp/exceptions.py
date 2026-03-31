"""Typed exceptions for Grocy API errors."""


class GrocyError(Exception):
    """Base exception for all Grocy errors."""


class GrocyAuthError(GrocyError):
    """Raised on 401/403 -- bad or missing API key."""


class GrocyValidationError(GrocyError):
    """Raised on 400 -- invalid request data."""


class GrocyNotFoundError(GrocyError):
    """Raised on 404 -- entity not found."""


class GrocyServerError(GrocyError):
    """Raised on 500 -- Grocy server error."""


class GrocyResolveError(GrocyError):
    """Raised when name-to-ID resolution fails (zero or ambiguous matches)."""
