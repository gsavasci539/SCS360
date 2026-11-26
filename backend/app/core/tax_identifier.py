"""Encryption and lookup fingerprints for organization tax identifiers."""

import base64
import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken


_FINGERPRINT_DOMAIN = b"scs360/organization-tax-identifier/fingerprint/v1\0"


def _fernet(key: str | None) -> Fernet:
    if not key:
        raise RuntimeError("Organization tax identifier encryption key is not configured")
    try:
        return Fernet(key.encode("ascii"))
    except (UnicodeEncodeError, ValueError):
        raise RuntimeError("Organization tax identifier encryption key is invalid") from None


def normalize_tax_identifier(value: str) -> str:
    return value.strip()


def encrypt_tax_identifier(value: str, key: str | None) -> str:
    normalized = normalize_tax_identifier(value)
    if not normalized:
        raise ValueError("Tax identifier cannot be blank")
    return _fernet(key).encrypt(normalized.encode("utf-8")).decode("ascii")


def decrypt_tax_identifier(ciphertext: str, key: str | None) -> str:
    try:
        return _fernet(key).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError, UnicodeDecodeError):
        raise RuntimeError("Organization tax identifier cannot be decrypted") from None


def tax_identifier_fingerprint(value: str, key: str | None) -> str:
    """Return a keyed, domain-separated digest for equality lookup only."""
    normalized = normalize_tax_identifier(value)
    if not normalized:
        raise ValueError("Tax identifier cannot be blank")
    _fernet(key)
    raw_key = base64.urlsafe_b64decode(key.encode("ascii"))
    lookup_key = hashlib.sha256(_FINGERPRINT_DOMAIN + raw_key).digest()
    return hmac.new(lookup_key, normalized.encode("utf-8"), hashlib.sha256).hexdigest()
