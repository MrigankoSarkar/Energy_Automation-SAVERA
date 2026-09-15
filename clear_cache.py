import os
import shutil
import sys

def clear_python_cache(root_dir):
    # Folders to ignore so we don't wipe the virtual environment
    ignore_dirs = {'.venv', 'venv', 'env', '.git', 'build', 'dist'}
    
    deleted_folders = 0
    deleted_files = 0

    print(f"Scanning '{root_dir}' for cache files...")

    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        # Modify dirnames in-place to prevent os.walk from entering ignored directories
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        # Remove __pycache__ directories
        for dirname in dirnames:
            if dirname == '__pycache__':
                full_path = os.path.join(dirpath, dirname)
                try:
                    shutil.rmtree(full_path)
                    deleted_folders += 1
                    print(f"Removed folder: {full_path}")
                except Exception as e:
                    print(f"Error removing {full_path}: {e}")

        # Remove leftover individual .pyc or .pyo files
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
    current_dir = os.path.dirname(os.path.abspath(__file__))
    clear_python_cache(current_dir)