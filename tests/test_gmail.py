import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gmail_service import authenticate_gmail

service = authenticate_gmail()
profile = service.users().getProfile(userId="me").execute()
print("Gmail connection OK:", profile.get("emailAddress"))
