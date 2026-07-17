"""
统一异常处理系统

定义后端服务的自定义异常类，提供统一的错误响应格式。
"""


class BackendException(Exception):
    """基础异常类

    所有后端异常的基类，提供统一的错误码、消息和详情字段。
    """

    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self):
        """转换为字典格式，用于API响应"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


class DataUnavailableException(BackendException):
    """数据不可用异常

    当数据源暂时不可用或数据获取失败时抛出。
    """

    def __init__(self, message: str = "Data source unavailable", details: dict = None):
        super().__init__("DATA_SOURCE_UNAVAILABLE", message, details)


class ValidationException(BackendException):
    """数据验证异常

    当请求参数验证失败时抛出。
    """

    def __init__(self, message: str = "Validation failed", details: dict = None):
        super().__init__("VALIDATION_ERROR", message, details)


class ExternalServiceException(BackendException):
    """外部服务异常

    当外部服务（如Agent服务）调用失败时抛出。
    """

    def __init__(self, message: str = "External service error", details: dict = None):
        super().__init__("EXTERNAL_SERVICE_ERROR", message, details)


class ResourceNotFoundException(BackendException):
    """资源不存在异常

    当请求的资源不存在时抛出。
    """

    def __init__(self, message: str = "Resource not found", details: dict = None):
        super().__init__("RESOURCE_NOT_FOUND", message, details)


class DatabaseException(BackendException):
    """数据库异常

    当数据库操作失败时抛出。
    """

    def __init__(self, message: str = "Database error", details: dict = None):
        super().__init__("DATABASE_ERROR", message, details)


class RateLimitExceededException(BackendException):
    """速率限制异常

    当超过API调用速率限制时抛出。
    """

    def __init__(self, message: str = "Rate limit exceeded", details: dict = None):
        super().__init__("RATE_LIMIT_EXCEEDED", message, details)
