import pytest

from app.utils.error_handler import ErrorCode, ErrorResponse


def test_success_response_default_message_and_no_data():
    resp = ErrorResponse.success_response()
    assert resp["code"] == ErrorCode.SUCCESS.value
    assert resp["message"] == "成功"
    assert "data" not in resp


def test_success_response_with_data():
    data = {"a": 1}
    resp = ErrorResponse.success_response("OK", data)
    assert resp["code"] == 200
    assert resp["message"] == "OK"
    assert resp["data"] == {"a": 1}


def test_success_response_with_extra_data():
    data = {"x": 2}
    extra = {"trace": "abc"}
    resp = ErrorResponse.success_response_with_extra_data("OK", data=data, extra_data=extra)
    assert resp["code"] == 200
    assert resp["message"] == "OK"
    assert resp["data"] == {"x": 2}
    assert resp["extra_data"] == {"trace": "abc"}


def test_create_error_response_enum_and_code():
    enum_resp = ErrorResponse.create_error_response(ErrorCode.NOT_FOUND, "missing")
    assert enum_resp["code"] == 404
    assert enum_resp["message"] == "missing"
    assert enum_resp["data"] == {}

    code_resp = ErrorResponse.create_error_code_response(415, "bad type", data={"t": 1})
    assert code_resp["code"] == 415
    assert code_resp["message"] == "bad type"
    assert code_resp["data"] == {"t": 1}
