class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, errors: list | None = None):
        self.message = message
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Kayıt bulunamadı"):
        super().__init__(message, status_code=404)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Yetkilendirme gerekli"):
        super().__init__(message, status_code=401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Bu işlem için yetkiniz yok"):
        super().__init__(message, status_code=403)


class ValidationException(AppException):
    def __init__(self, message: str = "Doğrulama hatası", errors: list | None = None):
        super().__init__(message, status_code=422, errors=errors)


class ConflictException(AppException):
    def __init__(self, message: str = "Kayıt zaten mevcut"):
        super().__init__(message, status_code=409)
