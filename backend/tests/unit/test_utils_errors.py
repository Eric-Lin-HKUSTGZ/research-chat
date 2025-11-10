import pytest

from app.utils.errors import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    DatabaseError,
    ExternalServiceError,
)


def assert_error(err, cls, msg, code):
    assert isinstance(err, cls)
    assert err.message == msg
    assert err.code == code


def test_custom_errors_hierarchy_and_fields():
    assert_error(APIError("oops", code=500), APIError, "oops", 500)
    assert_error(AuthenticationError(), AuthenticationError, "Authentication failed", 401)
    assert_error(AuthorizationError(), AuthorizationError, "Authorization failed", 403)
    assert_error(ValidationError(), ValidationError, "Validation failed", 400)
    assert_error(NotFoundError(), NotFoundError, "Resource not found", 404)
    assert_error(ConflictError(), ConflictError, "Resource conflict", 409)
    assert_error(RateLimitError(), RateLimitError, "Rate limit exceeded", 429)
    assert_error(ServerError(), ServerError, "Internal server error", 500)
    assert_error(ServiceUnavailableError(), ServiceUnavailableError, "Service unavailable", 503)
    assert_error(DatabaseError(), DatabaseError, "Database error", 500)
    assert_error(ExternalServiceError(), ExternalServiceError, "External service error", 502)
