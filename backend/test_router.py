import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Test if individual routers work
try:
    from app.routers import auth
    print(f"Auth router: {len(auth.router.routes)} routes")
    for r in auth.router.routes:
        if hasattr(r, 'path'):
            print(f"  {r.path}")
except Exception as e:
    print(f"Auth error: {e}")

try:
    from app.routers import students
    print(f"Students router: {len(students.router.routes)} routes")
    for r in students.router.routes:
        if hasattr(r, 'path'):
            print(f"  {r.path}")
except Exception as e:
    print(f"Students error: {e}")
