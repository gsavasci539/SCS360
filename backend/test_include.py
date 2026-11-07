import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI

app = FastAPI()

try:
    from app.routers import auth
    app.include_router(auth.router)
    print(f"After including auth: {len([r for r in app.routes if hasattr(r, 'path')])} routes with path")
except Exception as e:
    print(f"Error including auth: {e}")
    import traceback
    traceback.print_exc()

try:
    from app.routers import students
    app.include_router(students.router)
    print(f"After including students: {len([r for r in app.routes if hasattr(r, 'path')])} routes with path")
except Exception as e:
    print(f"Error including students: {e}")
    import traceback
    traceback.print_exc()

print("Final routes with path:")
for r in app.routes:
    if hasattr(r, 'path'):
        print(f"  {r.path}")
