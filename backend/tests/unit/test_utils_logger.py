import io
import logging
import os
from datetime import datetime

from app.utils.logger import SimpleFormatter, ColorFormatter, _BelowErrorFilter, DailySwitchingFileHandler, get_logger


def test_simple_formatter_outputs_expected_fields():
    fmt = SimpleFormatter()
    logger = logging.getLogger("t1")
    logger.setLevel(logging.DEBUG)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(fmt)
    logger.handlers[:] = [handler]

    logger.info("hello")
    s = stream.getvalue()
    assert "[INFO]" in s and "hello" in s and ":" in s


def test_color_formatter_wraps_base():
    fmt = ColorFormatter()
    logger = logging.getLogger("t2")
    logger.setLevel(logging.DEBUG)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(fmt)
    logger.handlers[:] = [handler]

    logger.error("boom")
    s = stream.getvalue()
    # Should contain ANSI reset code
    assert "\x1b[0m" in s and "boom" in s


def test_below_error_filter_allows_only_below_error():
    f = _BelowErrorFilter()
    rec_info = logging.LogRecord("n", logging.INFO, __file__, 1, "i", args=(), exc_info=None)
    rec_err = logging.LogRecord("n", logging.ERROR, __file__, 1, "e", args=(), exc_info=None)
    assert f.filter(rec_info) is True
    assert f.filter(rec_err) is False


def test_daily_switching_file_handler_filename(tmp_path):
    log_dir = tmp_path / "logs"
    h = DailySwitchingFileHandler(str(log_dir), for_error=False)
    # emit a message to ensure file is created
    logger = logging.getLogger("t3")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(h)
    logger.debug("hi")

    d = datetime.now().strftime("%Y%m%d")
    path = os.path.join(str(log_dir), f"{d}.log")
    assert os.path.exists(path)
    h.close()


def test_get_logger_returns_logger():
    lg = get_logger("any")
    lg.info("x")
    assert isinstance(lg, logging.Logger)
