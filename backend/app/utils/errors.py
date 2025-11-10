"""
自定义异常类
Custom Exception Classes
"""


class APIError(Exception):
    """API基础异常类"""
    def __init__(self, message: str, code: int = 500, data=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data


class AuthenticationError(APIError):
    """认证错误"""
    def __init__(self, message: str = "Authentication failed", data=None):
        super().__init__(message, code=401, data=data)


class AuthorizationError(APIError):
    """授权错误"""
    def __init__(self, message: str = "Authorization failed", data=None):
        super().__init__(message, code=403, data=data)


class ValidationError(APIError):
    """验证错误"""
    def __init__(self, message: str = "Validation failed", data=None):
        super().__init__(message, code=400, data=data)


class NotFoundError(APIError):
    """资源未找到错误"""
    def __init__(self, message: str = "Resource not found", data=None):
        super().__init__(message, code=404, data=data)


class ConflictError(APIError):
    """冲突错误"""
    def __init__(self, message: str = "Resource conflict", data=None):
        super().__init__(message, code=409, data=data)


class RateLimitError(APIError):
    """速率限制错误"""
    def __init__(self, message: str = "Rate limit exceeded", data=None):
        super().__init__(message, code=429, data=data)


class ServerError(APIError):
    """服务器内部错误"""
    def __init__(self, message: str = "Internal server error", data=None):
        super().__init__(message, code=500, data=data)


class ServiceUnavailableError(APIError):
    """服务不可用错误"""
    def __init__(self, message: str = "Service unavailable", data=None):
        super().__init__(message, code=503, data=data)


class DatabaseError(APIError):
    """数据库错误"""
    def __init__(self, message: str = "Database error", data=None):
        super().__init__(message, code=500, data=data)


class ExternalServiceError(APIError):
    """外部服务错误"""
    def __init__(self, message: str = "External service error", data=None):
        super().__init__(message, code=502, data=data)
