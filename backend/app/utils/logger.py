import logging
import os
import sys
from datetime import datetime
from typing import Optional

_logger_instance: Optional[logging.Logger] = None
_log_dir: Optional[str] = None


class SimpleFormatter(logging.Formatter):
    """简化的日志格式器，用于生产环境"""

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname
        lineno = record.lineno
        message = record.getMessage()

        if record.exc_info:
            message += f" | Exception: {record.exc_info[1]}"

        if level == 'ERROR':
            return f"[ERROR] {timestamp} | {record.filename}:{lineno} | {message}"
        elif level == 'WARNING':
            return f"[WARN]  {timestamp} | {record.filename}:{lineno} | {message}"
        elif level == 'INFO':
            return f"[INFO]  {timestamp} | {record.filename}:{lineno} | {message}"
        elif level == 'DEBUG':
            return f"[DEBUG] {timestamp} | {record.filename}:{lineno} | {message}"
        else:
            return f"[{level}] {timestamp} | {record.filename}:{lineno} | {message}"


class ColorFormatter(SimpleFormatter):
    RESET = "\x1b[0m"
    COLORS = {
        'DEBUG': "\x1b[37m",
        'INFO': "\x1b[32m",
        'WARNING': "\x1b[33m",
        'ERROR': "\x1b[31m",
        'CRITICAL': "\x1b[1;31m"
    }

    def format(self, record):
        base = super().format(record)
        color = self.COLORS.get(record.levelname, '')
        reset = self.RESET if color else ''
        return f"{color}{base}{reset}"


class _BelowErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < logging.ERROR


class DailySwitchingFileHandler(logging.Handler):
    def __init__(self, log_dir: str, for_error: bool = False, encoding: str = 'utf-8'):
        level = logging.ERROR if for_error else logging.DEBUG
        super().__init__(level=level)
        self.log_dir = log_dir
        self.for_error = for_error
        self.encoding = encoding
        self._current_date = None
        self._stream = None
        self._rollover_if_needed()

    def _date_str(self) -> str:
        return datetime.now().strftime('%Y%m%d')

    def _filepath(self) -> str:
        d = self._date_str()
        name = f"{d}_error.log" if self.for_error else f"{d}.log"
        return os.path.join(self.log_dir, name)

    def _rollover_if_needed(self):
        os.makedirs(self.log_dir or '.', exist_ok=True)
        d = self._date_str()
        if self._current_date != d:
            if self._stream:
                try:
                    self._stream.close()
                except Exception:
                    pass
            self._current_date = d
            self._stream = open(self._filepath(), 'a', encoding=self.encoding)

    def emit(self, record: logging.LogRecord):
        try:
            self._rollover_if_needed()
            if self.for_error:
                if record.levelno >= logging.ERROR:
                    msg = self.format(record)
                    self._stream.write(msg + "\n")
                    self._stream.flush()
            else:
                msg = self.format(record)
                self._stream.write(msg + "\n")
                self._stream.flush()
        except Exception:
            self.handleError(record)

    def close(self):
        try:
            if self._stream:
                self._stream.close()
        finally:
            super().close()


def _current_trace_id():
    """获取当前追踪ID（FastAPI中从contextvars获取）"""
    try:
        from contextvars import ContextVar
        # FastAPI使用contextvars存储请求上下文
        # 这里暂时返回None，因为FastAPI的trace_id在中间件中处理
        return None
    except Exception:
        return None


class TraceContextLogger(logging.Logger):
    def _inject(self, msg):
        tid = _current_trace_id()
        if not tid:
            return msg
        try:
            if isinstance(msg, str):
                return f"{msg} | trace_id={tid}"
            return msg
        except Exception:
            return msg

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1, **kwargs):
        msg = self._inject(msg)
        super()._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel+1, **kwargs)


def _init_logger(log_dir: str = None, log_level: str = 'INFO', max_bytes: int = 10 * 1024 * 1024, backup_count: int = 30):
    global _logger_instance, _log_dir
    if _logger_instance is not None:
        return _logger_instance
    _log_dir = log_dir
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    logging.setLoggerClass(TraceContextLogger)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(SimpleFormatter())
    root_logger.addHandler(console_handler)

    if log_dir:
        # 日常日志文件 - 记录所有级别
        info_handler = DailySwitchingFileHandler(log_dir=log_dir, for_error=False)
        info_handler.setLevel(logging.DEBUG)
        info_handler.setFormatter(SimpleFormatter())
        root_logger.addHandler(info_handler)

        # 错误日志文件 - 只记录ERROR及以上
        error_handler = DailySwitchingFileHandler(log_dir=log_dir, for_error=True)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(SimpleFormatter())
        root_logger.addHandler(error_handler)

    _logger_instance = root_logger
    return _logger_instance


def setup_logger(name: str = None, level: str = 'INFO') -> logging.Logger:
    global _logger_instance
    if _logger_instance is None:
        base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        log_dir = os.path.join(base_dir, "logs")
        log_max_bytes = int(os.getenv('LOG_MAX_BYTES', str(10 * 1024 * 1024)))
        log_backup_count = int(os.getenv('LOG_BACKUP_COUNT', '30'))
        _init_logger(log_dir=log_dir, log_level=level, max_bytes=log_max_bytes, backup_count=log_backup_count)
    if name:
        return logging.getLogger(name)
    else:
        return _logger_instance


def get_logger(name: str = None, level: str = 'INFO') -> logging.Logger:
    """
    获取日志记录器
    所有模块的日志都会输出到同一个文件
    """
    return setup_logger(name, level)
