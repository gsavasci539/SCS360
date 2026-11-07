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
