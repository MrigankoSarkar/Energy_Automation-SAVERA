"""
Utility script to clear Python __pycache__ and compiled bytecode files across the repository.
"""

import os
import shutil
import sys
from pathlib import Path


def clear_python_cache(root_dir: str | Path) -> None:
    ignore_dirs = {'.venv', 'venv', 'env', '.git', 'build', 'dist', '.pytest_cache'}
    deleted_folders = 0
    deleted_files = 0

    print(f"Scanning '{root_dir}' for cache files...")

    for dirpath, dirnames, filenames in os.walk(str(root_dir), topdown=False):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        for dirname in dirnames:
            if dirname == '__pycache__':
                full_path = os.path.join(dirpath, dirname)
                try:
                    shutil.rmtree(full_path)
                    deleted_folders += 1
                    print(f"Removed folder: {full_path}")
                except Exception as e:
                    print(f"Error removing {full_path}: {e}")

        for filename in filenames:
            if filename.endswith(('.pyc', '.pyo', '.pyd')):
                full_path = os.path.join(dirpath, filename)
                try:
                    os.remove(full_path)
                    deleted_files += 1
                    print(f"Removed file: {full_path}")
                except Exception as e:
                    print(f"Error removing {full_path}: {e}")

    print("\n--- Cache Cleanup Complete ---")
    print(f"Removed {deleted_folders} '__pycache__' folders.")
    print(f"Removed {deleted_files} individual bytecode files.")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    clear_python_cache(repo_root)
