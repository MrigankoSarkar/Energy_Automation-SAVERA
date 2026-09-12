import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import load_config, project_path

config = load_config()
path = project_path(config["excel"]["file"])
print("Configured workbook:", path)
print("Exists:", path.exists())
