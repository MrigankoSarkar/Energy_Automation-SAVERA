import logging
from config import PROJECT_ROOT

LOG_DIRECTORY = PROJECT_ROOT / "data" / "logs"
LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIRECTORY / "automation.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)

def info(message): logging.info(message)
def warning(message): logging.warning(message)
def error(message): logging.error(message)
def exception(message): logging.exception(message)
