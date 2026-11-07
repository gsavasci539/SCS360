"""Export the same OpenAPI contract served at /api/openapi.json for mobile SDKs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.main import app

if __name__ == "__main__":
    path = ROOT.parent / "docs" / "openapi.json"
    path.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OpenAPI contract exported to {path}")
