from app.routes.auth import create_response


def test_create_response_defaults():
    resp = create_response()
    assert resp["code"] == 200
    assert resp["message"] == "Success"
    assert resp["success"] is True
    assert resp["data"] == {}


def test_create_response_error_code_sets_success_false():
    resp = create_response(code=404, message="Not found", data={"x": 1})
    assert resp["code"] == 404
    assert resp["message"] == "Not found"
    assert resp["success"] is False
    assert resp["data"] == {"x": 1}
