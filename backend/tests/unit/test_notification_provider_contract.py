import httpx
import pytest
from types import SimpleNamespace
from app.infrastructure.notifications.sms_provider import NetgsmSmsProvider


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,expected", [
    ({"code": "00", "jobid": "test-job-id"}, True),
    ({"code": "30", "description": "invalid credentials"}, False),
    ({"code": "00"}, False),
])
async def test_sms_requires_real_provider_acceptance_not_only_http_200(monkeypatch, payload, expected):
    original_client = httpx.AsyncClient
    def handler(request):
        assert request.method == "POST"
        assert request.headers["authorization"].startswith("Basic ")
        assert b'"messages"' in request.content
        return httpx.Response(200, json=payload)
    monkeypatch.setattr("app.infrastructure.notifications.sms_provider.httpx.AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs))
    settings = SimpleNamespace(NOTIFICATION_DELIVERY_ENABLED=True, NOTIFICATION_TIMEOUT_SECONDS=1,
        SMS_API_URL="https://api.netgsm.com.tr/sms/rest/v2/send", SMS_USERNAME="test", SMS_PASSWORD="test", SMS_HEADER="TEST")
    result = await NetgsmSmsProvider(settings).send("test-recipient", None, "No real SMS is sent")
    assert result.success is expected
