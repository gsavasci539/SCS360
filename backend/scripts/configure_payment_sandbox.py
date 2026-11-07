"""Prepare explicit sandbox settings; no key arguments, DB writes or provider calls."""
import argparse
from contextlib import redirect_stderr
from datetime import UTC, datetime
from io import StringIO
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryptography.fernet import Fernet
from dotenv import dotenv_values

from app.application.services.payment_readiness import SANDBOX_URL, configuration


class SetupError(ValueError):
    pass


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # Unknown arguments may contain mistakenly supplied keys: never echo them.
        self.exit(2, '{"written":false,"message":"Geçersiz seçenek; --help ile güvenli seçenekleri inceleyin"}\n')


def prepare(original, target, *, callback_url=None, portal_url=None, organization_id=None, activate=False):
    """Patch only requested lines, preserving unrelated bytes and existing keys."""
    if target not in {"saas", "school"}:
        raise SetupError("Geçersiz ödeme hedefi")
    text = original.decode("utf-8-sig")
    with redirect_stderr(StringIO()):
        source = dict(dotenv_values(stream=StringIO(text), interpolate=False))
    environment = str(source.get("APP_ENV") or "development").lower()
    effective = str(os.environ.get("APP_ENV") or environment).lower()
    if environment not in {"development", "test"} or effective not in {"development", "test"}:
        raise SetupError("Sandbox hazırlığı yalnız development/test ortamında yapılabilir")
    prefix = "SAAS_IYZICO_" if target == "saas" else "IYZICO_"
    changes = {}

    def assign(field, proposed):
        if proposed is None:
            return
        if any(character in proposed for character in ("\r", "\n", "\x00", '"', "'")):
            raise SetupError(f"Geçersiz değer: {field}")
        if os.environ.get(field) and os.environ[field] != proposed:
            raise SetupError(f"İşlem ortamı dosya ayarını geçersiz kılıyor: {field}")
        previous = source.get(field)
        if previous and previous != proposed:
            raise SetupError(f"Mevcut ayar otomatik değiştirilmez: {field}")
        if previous != proposed:
            source[field] = proposed
            changes[field] = proposed

    assign(prefix + "BASE_URL", SANDBOX_URL)
    assign(prefix + "CALLBACK_URL", callback_url)
    if target == "school":
        if not organization_id:
            raise SetupError("Öğrenci ödemesi için açık kurum UUID seçimi zorunludur")
        try:
            assign("IYZICO_ORGANIZATION_ID", str(UUID(str(organization_id))))
        except ValueError as exc:
            if isinstance(exc, SetupError):
                raise
            raise SetupError("Geçersiz kurum UUID") from exc
    else:
        if organization_id:
            raise SetupError("SaaS üyelik hesabına kurum UUID bağlanmaz")
        assign("SAAS_PORTAL_URL", portal_url)
        if not source.get("SAAS_CHECKOUT_ENCRYPTION_KEY"):
            assign("SAAS_CHECKOUT_ENCRYPTION_KEY", Fernet.generate_key().decode())
    readiness = configuration(source, target)
    if readiness["invalid_fields"] or readiness["state"] == "blocked_environment":
        raise SetupError("Geçersiz ödeme ayarı: " + ", ".join(readiness["invalid_fields"]))
    flag = readiness["activation_field"]
    if activate:
        if not readiness["configured"]:
            raise SetupError("Etkinleştirilemedi; eksik alanlar: " + ", ".join(readiness["missing_fields"]))
        previous = str(source.get(flag) or "false").lower()
        if os.environ.get(flag) and os.environ[flag].lower() not in {"true", "1", "yes", "on"}:
            raise SetupError(f"İşlem ortamı etkinleştirmeyi engelliyor: {flag}")
        if previous not in {"true", "1", "yes", "on"}:
            source[flag] = "true"
            changes[flag] = "true"
    elif flag not in source:
        source[flag] = "false"
        changes[flag] = "false"
    newline = "\r\n" if b"\r\n" in original else "\n"
    for field, proposed in changes.items():
        pattern = re.compile(r"^[ \t]*(?:export[ \t]+)?" + re.escape(field) + r"[ \t]*=.*$", re.MULTILINE)
        matches = list(pattern.finditer(text))
        if len(matches) > 1:
            raise SetupError(f"Aynı ayar birden çok kez tanımlı: {field}")
        replacement = f"{field}={proposed}"
        if matches:
            match = matches[0]
            suffix = "\r" if match.group().endswith("\r") else ""
            text = text[:match.start()] + replacement + suffix + text[match.end():]
        else:
            text = text + (newline if text and not text.endswith(("\n", "\r")) else "") + replacement + newline
    updated = (b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b"") + text.encode("utf-8")
    return updated, {"target": target, "changed_fields": list(changes), "configuration": configuration(source, target)}


def write_environment(path, original, updated):
    if path.is_symlink():
        raise SetupError("Sembolik ayar dosyasına yazılmaz")
    if not path.exists() or path.read_bytes() != original:
        raise SetupError("Ayar dosyası değişti; yeniden kontrol edin")
    if original == updated:
        return False
    backup = path.with_name(".env.sandbox-backup-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex)
    with os.fdopen(os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as handle:
        handle.write(original)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".env.sandbox-tmp-", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(updated); handle.flush(); os.fsync(handle.fileno())
        if path.read_bytes() != original:
            raise SetupError("Ayar dosyası değişti; yazma iptal edildi")
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return True


def main():
    parser = SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, choices=("saas", "school"))
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--callback-url")
    parser.add_argument("--portal-url")
    parser.add_argument("--organization-id")
    parser.add_argument("--activate", action="store_true", help="Requires complete existing sandbox keys and explicit --write")
    parser.add_argument("--write", action="store_true", help="Write checked settings; otherwise show field names only")
    args = parser.parse_args()
    try:
        if args.activate and not args.write:
            raise SetupError("Etkinleştirme için --write açıkça verilmelidir")
        original = args.env_file.read_bytes()
        updated, result = prepare(original, args.target, callback_url=args.callback_url,
            portal_url=args.portal_url, organization_id=args.organization_id, activate=args.activate)
        result["written"] = write_environment(args.env_file, original, updated) if args.write else False
        result["dry_run"] = not args.write
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, SetupError) as exc:
        message = str(exc) if isinstance(exc, SetupError) else "Ayar dosyası güvenle okunamadı veya yazılamadı"
        print(json.dumps({"written": False, "message": message}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
