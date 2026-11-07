from app.core.config import get_settings


class IyzicoConfig:
    @staticmethod
    def get_options():
        settings = get_settings()
        return {"api_key": settings.IYZICO_API_KEY, "secret_key": settings.IYZICO_SECRET_KEY,
            "base_url": settings.IYZICO_BASE_URL.removeprefix("https://").rstrip("/")}
