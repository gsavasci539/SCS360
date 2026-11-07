import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import traceback

try:
    from app.routers import debts
    print("Debts imported successfully")
except Exception as e:
    print(f"Error importing debts: {e}")
    traceback.print_exc()

try:
    from app.routers import auth
    print("Auth imported successfully")
except Exception as e:
    print(f"Error importing auth: {e}")
    traceback.print_exc()

try:
    from app.main import app
    print(f"App loaded. Routes: {len([r for r in app.routes if hasattr(r, 'path')])}")
except Exception as e:
    print(f"Error importing app: {e}")
    traceback.print_exc()
