"""Fail closed when a chatbot provider could transfer prompt data externally."""

from urllib.parse import urlsplit


_INTERNAL_LLM_HOSTS = {"localhost", "127.0.0.1", "::1", "ollama"}


def enforce_chatbot_transfer_policy(
    provider_type: str,
    endpoint: str | None,
    *,
    external_transfer_allowed: bool,
    allowed_external_hosts: set[str] | None = None,
) -> None:
    if provider_type == "mock":
        return
    if not endpoint:
        raise ValueError("Chatbot provider endpoint is required")

    parsed = urlsplit(endpoint)
    host = (parsed.hostname or "").lower()
    internal = host in _INTERNAL_LLM_HOSTS
    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Chatbot provider endpoint is invalid")
    if internal:
        return
    allowed_hosts = {
        item.strip().lower().rstrip(".") for item in (allowed_external_hosts or set())
    }
    if (
        not external_transfer_allowed
        or parsed.scheme != "https"
        or parsed.port not in (None, 443)
        or host not in allowed_hosts
    ):
        raise ValueError(
            "External chatbot transfer requires explicit approval, HTTPS and an exact host allowlist"
        )
