from app.core.responses import success_response


def test_legacy_error_response_preserves_failure_and_message():
    response = success_response(None, "Kayıt bulunamadı", success=False)
    assert response == {"success": False, "message": "Kayıt bulunamadı", "data": None}


async def test_ambiguous_legacy_identifier_is_a_conflict_without_exposing_data():
    import json
    from starlette.requests import Request
    from sqlalchemy.exc import MultipleResultsFound
    from app.core.middleware import generic_exception_handler
    request = Request({"type": "http", "method": "GET", "path": "/api/students/legacy-id", "headers": []})
    request.state.request_id = "test-request"
    response = await generic_exception_handler(request, MultipleResultsFound("private SQL and student details"))
    assert response.status_code == 409
    body = json.loads(response.body)
    assert body["success"] is False and body["request_id"] == "test-request"
    assert "private SQL" not in response.body.decode()


async def test_unhandled_exception_log_does_not_include_sensitive_exception_message(caplog):
    import logging
    from starlette.requests import Request
    from app.core.middleware import generic_exception_handler

    caplog.set_level(logging.ERROR)
    request = Request({"type": "http", "method": "POST", "path": "/api/checkout", "headers": []})
    request.state.request_id = "test-request"
    response = await generic_exception_handler(request, RuntimeError("TCKN-SENSITIVE-SENTINEL"))
    assert response.status_code == 500
    assert "TCKN-SENSITIVE-SENTINEL" not in caplog.text
    assert "RuntimeError" in caplog.text and "test-request" in caplog.text


async def test_http_exception_does_not_echo_structured_sensitive_detail():
    import json
    from fastapi import HTTPException
    from starlette.requests import Request
    from app.core.middleware import http_exception_handler

    request = Request({"type": "http", "method": "POST", "path": "/api/checkout", "headers": []})
    request.state.request_id = "test-request"
    response = await http_exception_handler(request, HTTPException(502, detail={"buyer": "TCKN-SENSITIVE-SENTINEL"}))
    body = json.loads(response.body)
    assert response.status_code == 502
    assert body["message"] == "İstek tamamlanamadı" and body["detail"] == "İstek tamamlanamadı"
    assert "TCKN-SENSITIVE-SENTINEL" not in response.body.decode()


async def test_http_exception_keeps_safe_string_detail_compatibility():
    import json
    from fastapi import HTTPException
    from starlette.requests import Request
    from app.core.middleware import http_exception_handler

    request = Request({"type": "http", "method": "GET", "path": "/api/organizations", "headers": []})
    response = await http_exception_handler(request, HTTPException(404, detail="Kurum 123.456.789.01 bulunamadı"))
    body = json.loads(response.body)
    assert response.status_code == 404 and body["message"] == "Kurum [gizlendi] bulunamadı"
    assert body["detail"] == "Kurum [gizlendi] bulunamadı"


async def test_application_exception_redacts_tckn_from_messages_and_structured_errors():
    import json
    from starlette.requests import Request
    from app.core.exceptions import AppException
    from app.core.middleware import app_exception_handler

    request = Request({"type": "http", "method": "POST", "path": "/api/checkout", "headers": []})
    response = await app_exception_handler(request, AppException("Kimlik 123-456-78901 doğrulanamadı", errors=[{"received": "123.456.789.01"}]))
    body = json.loads(response.body)
    assert body["message"] == "Kimlik [gizlendi] doğrulanamadı"
    assert body["errors"] == [{"received": "[gizlendi]"}]
    assert "123-456-78901" not in response.body.decode() and "123.456.789.01" not in response.body.decode()


async def test_actual_application_handlers_treat_ambiguous_identifiers_as_http_conflicts():
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.exc import MultipleResultsFound
    from app.main import app
    from app.core.middleware import RequestLoggingMiddleware
    probe = FastAPI(exception_handlers=app.exception_handlers)
    probe.add_middleware(RequestLoggingMiddleware)
    @probe.get("/legacy")
    async def legacy():
        raise MultipleResultsFound("sensitive database details")
    async with AsyncClient(transport=ASGITransport(app=probe), base_url="http://test") as client:
        response = await client.get("/legacy")
    assert response.status_code == 409
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "sensitive database" not in response.text
