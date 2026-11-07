"""Export the server's analytics permissions for optional UI requests."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core.analysis_access import POLICY

if __name__ == "__main__":
    path = ROOT.parent / "frontend/src/config/analysisPermissions.json"
    path.write_text(json.dumps({"/ai" + key: value for key, value in POLICY.items()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(POLICY)} analytics permission rules")
