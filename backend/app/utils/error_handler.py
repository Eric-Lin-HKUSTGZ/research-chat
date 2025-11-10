from typing import Dict, Any, Optional
from enum import Enum


class ErrorCode(Enum):
    """统一的错误码枚举，对应HTTP状态码"""
    # 成功
    SUCCESS = 200

    # 客户端错误 4xx
    BAD_REQUEST = 400  # 请求参数错误
    UNAUTHORIZED = 401  # 未授权/认证失败
    FORBIDDEN = 403    # 禁止访问
    NOT_FOUND = 404    # 资源不存在
    CONFLICT = 409     # 资源冲突（如用户已注册）
    UNSUPPORTED_MEDIA_TYPE = 415  # 不支持的媒体类型

    # 服务端错误 5xx
    INTERNAL_SERVER_ERROR = 500  # 服务器内部错误

    # HTTP 错误
    HTTP_ERROR = 0  # HTTP 错误，使用原始 HTTP 状态码

    # 特定业务错误
    CAPTCHA_INVALID = 400  # 验证码不正确
    PARAMETER_INVALID = 400  # 参数不正确
    EMAIL_NOT_REGISTERED = 402  # 邮箱未注册
    EMAIL_INVALID = 402  # 邮箱不正确
    PASSWORD_INVALID = 403  # 邮箱不正确
    USER_ALREADY_EXISTS = 409  # 用户已注册
    FILE_TOO_LARGE = 413  # 文件过大
    USER_NOT_FOUND = 404  # 用户不存在
    SAVE_FAILED = 500  # 保存失败
    DELETE_FAILED = 404  # 删除失败
    AVATAR_NOT_SET = 404  # 未设置头像
    USERNAME_EMPTY = 400  # 用户名不能为空
    AGENT_NOT_FOUND = 404  # AI Agent 不存在
    AGENT_NOT_VISIBLE = 403  # AI Agent 不可见
    SESSION_NOT_FOUND = 404  # 会话不存在
    DATA_NOT_FOUND = 404  # 数据不存在


class ErrorResponse:
    """统一的错误响应格式"""

    @staticmethod
    def create_error_response(
        error_code: ErrorCode,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建错误响应"""
        response = {
            "code": error_code.value,
            "message": message
        }
        response["data"] = data or {}
        return response

    @staticmethod
    def create_error_code_response(
        error_code: int,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建错误响应"""
        response = {
            "code": error_code,
            "message": message
        }
        response["data"] = data or {}
        return response

    @staticmethod
    def success_response(
        message: str = "成功",
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建成功响应"""
        response = {
            "code": ErrorCode.SUCCESS.value,
            "message": message
        }
        if data is not None:
            response["data"] = data
        return response

    @staticmethod
    def success_response_with_extra_data(
        message: str = "成功",
        data: Optional[Dict[str, Any]] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建成功响应"""
        response = {
            "code": ErrorCode.SUCCESS.value,
            "message": message,
            "extra_data": extra_data
        }
        if data is not None:
            response["data"] = data
        return response


class ErrorMessage:
    """统一的错误消息映射"""

    # 验证相关
    CAPTCHA_INVALID = "验证码不正确"
    PARAMETER_INVALID = "参数不正确"
    PARAMETER_INCOMPLETE = "参数不完整"
    EMAIL_FORMAT_INVALID = "邮箱格式不正确"
    PASSWORD_FORMAT_INVALID = "密码格式不正确"
    PASSWORD_STRENGTH_INVALID = "密码强度不正确"
    # 认证相关
    EMAIL_NOT_REGISTERED = "邮箱未注册"
    EMAIL_INVALID = "邮箱不正确"
    PASSWORD_INVALID = "密码不正确"
    UNAUTHORIZED = "未授权"

    # 用户相关
    USER_ALREADY_EXISTS = "用户已注册"
    USER_NOT_FOUND = "用户不存在"
    USERNAME_EMPTY = "用户名不能为空"
    AGENT_NOT_FOUND = "AI Agent 不存在"
    AGENT_NOT_VISIBLE = "AI Agent 不可见"
    SESSION_NOT_FOUND = "会话不存在"

    # 文件相关
    FILE_TOO_LARGE = "文件过大，限制 1MB"
    UNSUPPORTED_MEDIA_TYPE = "不支持的图片类型"
    NO_FILE_SELECTED = "未选择文件"
    NO_FILES_UPLOADED = "没有文件"
    DELETE_FAILED = "删除失败"
    AVATAR_NOT_SET = "未设置头像"

    # 操作相关
    SAVE_FAILED = "保存失败"
    UPDATE_FAILED = "修改失败"
    CREATE_FAILED = "创建失败"

    # 系统相关
    INTERNAL_SERVER_ERROR = "服务器内部错误"
    SERVICE_UNAVAILABLE = "服务不可用"

    # 通用
    SUCCESS = "成功"
    NOT_FOUND = "未找到"
    BAD_REQUEST = "请求错误"
