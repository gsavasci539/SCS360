from fastapi import Request
from slowapi import Limiter


def get_client_ip(request: Request) -> str:
    # The backend is only reachable through the bundled reverse proxy in Compose.
    # Nginx overwrites X-Real-IP, so a client-provided value cannot survive the hop.
    forwarded_ip = request.headers.get("x-real-ip")
    if forwarded_ip:
        return forwarded_ip
    return request.client.host if request.client else "unknown"


# Rate limit disabled for development
limiter = Limiter(key_func=get_client_ip, storage_uri="memory://", default_limits=[])
