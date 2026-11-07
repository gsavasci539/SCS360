import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Test if main.py loads correctly
try:
    from app.main import app
    print(f"App loaded. Total routes: {len(app.routes)}")
    print(f"Routes with path: {len([r for r in app.routes if hasattr(r, 'path')])}")
    print("All routes with path:")
    for r in app.routes:
        if hasattr(r, 'path'):
            print(f"  {r.path}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
