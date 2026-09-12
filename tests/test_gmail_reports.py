import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import load_config
from gmail_service import authenticate_gmail, search_messages
from automation_engine import build_gmail_query

config = load_config()
service = authenticate_gmail()
query = build_gmail_query(config)
print("Query:", query)
messages = search_messages(service, query)
print("Matching messages:", len(messages))
for m in messages:
    print(m["id"])
