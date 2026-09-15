import os
import sys
import subprocess
from pathlib import Path

try:
    from app.bootstrap.qt_app import run_application
except ModuleNotFoundError as exc:
    venv_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
        sys.exit(subprocess.call([str(venv_python)] + sys.argv))
    raise


if __name__ == "__main__":
    run_application()