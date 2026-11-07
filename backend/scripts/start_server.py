"""Migrate the database before starting the API process in a container."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, check=True)
os.chdir(root)
os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5006"])
