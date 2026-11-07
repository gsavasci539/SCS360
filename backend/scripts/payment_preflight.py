"""Inspect payment setup without network/DB access or displaying secrets."""
import argparse
from contextlib import redirect_stderr
from io import StringIO
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values

from app.application.services.payment_readiness import report


def read_environment(path):
    # Values from the process override dotenv, matching BaseSettings precedence.
    text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    with redirect_stderr(StringIO()):
        saved = dotenv_values(stream=StringIO(text), interpolate=False)
    return {**saved, **os.environ}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--target", choices=("saas", "school", "all"), default="all")
    args = parser.parse_args()
    try:
        result = report(read_environment(args.env_file))
        if args.target != "all":
            result = {"scope": "offline_configuration_only", args.target: result[args.target]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        checks = [result[name]["available"] for name in ("saas", "school") if name in result]
        return 0 if checks and all(checks) else 1
    except (OSError, UnicodeError, ValueError):
        print(json.dumps({"scope": "offline_configuration_only", "configuration_readable": False,
            "message": "Ödeme ayar dosyası okunamadı veya yapılandırma geçersiz"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
