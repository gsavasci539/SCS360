"""Lossless public integration views and credential-aware object patches.

This is masking at the API boundary, not encryption or provider activation.
Existing credential values are never returned to a settings reader.
"""
from copy import deepcopy
import math
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.core.exceptions import ValidationException


MASK = "***"
_MISSING = object()


class IntegrationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    config: dict[str, Any] = Field(default_factory=dict)
    # Omission retains an existing flag; new records start inactive.
    is_active: StrictBool = False


def _secret_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
    return normalized in {"pwd", "auth", "accesskey"} or any(part in normalized for part in (
        "password", "passwd", "passphrase", "secret", "token", "apikey", "privatekey",
        "authorization", "credential", "signingkey", "accesskey",
    ))


def _valid_json(value: Any, depth: int = 0) -> bool:
    # Guard malformed legacy JSON (including non-finite numbers) before a view
    # can trigger an HTTP serializer error. No invalid value is included in errors.
    if depth > 50:
        return False
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_valid_json(item, depth + 1) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _valid_json(item, depth + 1) for key, item in value.items())
    return False


def redact_config(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: MASK if _secret_key(key) else redact_config(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_config(item) for item in value]
    return value


def config_view(config: Any) -> tuple[dict | None, bool]:
    if not isinstance(config, dict) or not _valid_json(config):
        return None, True
    return redact_config(config), False


def _has_mask(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_mask(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_mask(item) for item in value)
    return isinstance(value, str) and value.strip() == MASK


def _has_blank_credential(value: Any) -> bool:
    if isinstance(value, dict):
        return any((_secret_key(key) and (item is None or isinstance(item, str) and not item.strip()))
            or _has_blank_credential(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_blank_credential(item) for item in value)
    return False


def _merge(existing: Any, patch: Any) -> Any:
    if isinstance(patch, dict):
        # A partial object cannot replace a scalar/list legacy value: that would
        # silently discard an unknown structure and any credentials inside it.
        if existing is not _MISSING and not isinstance(existing, dict):
            raise ValidationException("Mevcut ayar yapısı farklı; kayıt incelemesi gerekli")
        result = deepcopy(existing) if isinstance(existing, dict) else {}
        for key, value in patch.items():
            previous = result.get(key, _MISSING)
            if _secret_key(key):
                placeholder = value is None or isinstance(value, str) and (not value.strip() or value.strip() == MASK)
                if placeholder:
                    if previous is _MISSING and isinstance(value, str) and value.strip() == MASK:
                        raise ValidationException("Saklı değeri olmayan gizli alan maskeyle kaydedilemez")
                    # Empty new credentials are absent, not a usable credential.
                    continue
                # A credential container is still a partial object patch, not
                # permission to discard its unprovided password/token/options.
                result[key] = _merge(previous, value)
            else:
                result[key] = _merge(previous, value)
        return result
    if isinstance(patch, list) and _has_mask(patch):
        # Positions/labels are not stable identities. Only an unchanged masked
        # array can round-trip safely; edits require explicit unmasked values.
        if isinstance(existing, list) and patch == redact_config(existing):
            return deepcopy(existing)
        raise ValidationException("Maskeli liste düzenlemesi belirsiz; gizli değerler korunarak inceleme gerekli")
    if isinstance(patch, list) and _has_blank_credential(patch):
        raise ValidationException("Boş gizli alan içeren liste düzenlemesi belirsiz; kayıt incelemesi gerekli")
    if isinstance(patch, str) and patch.strip() == MASK:
        # Prevent accidental propagation of a mask even under an unknown key.
        raise ValidationException("Maske yeni bir ayar değeri olarak kaydedilemez")
    return deepcopy(patch)


def merge_config(existing: Any, patch: dict) -> dict:
    if not isinstance(existing, dict) or not _valid_json(existing):
        raise ValidationException("Eski entegrasyon kaydı inceleme gerektiriyor; otomatik değiştirilemez")
    if not isinstance(patch, dict) or not _valid_json(patch):
        raise ValidationException("Entegrasyon ayarları geçerli bir JSON nesnesi olmalı")
    return _merge(existing, patch)
