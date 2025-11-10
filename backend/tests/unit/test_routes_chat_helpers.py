import re

from app.routes.chat_routes import (
    get_localized_message,
    format_log_with_timestamp,
    generate_page_session_id,
)


def test_get_localized_message_defaults_and_keys():
    # Known key, default locale cn
    assert "研究任务启动" in get_localized_message("task_start")
    # English
    assert "Research task started!" in get_localized_message("task_start", locale="en")
    # Unknown key falls back to key
    assert get_localized_message("nonexistent_key").startswith("nonexistent_key")


def test_format_log_with_timestamp_format():
    msg = format_log_with_timestamp("hello")
    # [YYYY-MM-DD HH:MM:SS] hello
    assert msg.endswith(" hello")
    assert re.match(r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] ", msg)


def test_generate_page_session_id_with_and_without_header(monkeypatch):
    # With header value
    assert generate_page_session_id("page-abc") == "page-abc"
    # Without -> startswith page_ and suffixed by millis
    gen = generate_page_session_id()
    assert gen.startswith("page_")
    assert gen[len("page_"):].isdigit()
