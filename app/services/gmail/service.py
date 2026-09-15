import base64
import re
from email.utils import parsedate_to_datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailService:
    """Gmail adapter used by the EnergyAutomation service layer."""

    def __init__(
        self,
        credentials_dir: str,
        sender: str,
        subject_contains: str,
        search_days: int,
        download_dir: str,
        logger,
    ):
        self.credentials_dir = Path(credentials_dir)
        self.sender = sender
        self.subject_contains = subject_contains
        self.search_days = int(search_days)
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self.service = None

    def connect(self):
        token_path = self.credentials_dir / "token.json"
        credentials_path = self.credentials_dir / "credentials.json"
        creds = None

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(token_path), SCOPES
            )

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        if not creds or not creds.valid:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"Gmail credentials.json not found: {credentials_path}"
                )

            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json(), encoding="utf-8")

        self.service = build(
            "gmail",
            "v1",
            credentials=creds,
            cache_discovery=False,
        )
        return True

    def _ensure_connected(self):
        if self.service is None:
            self.connect()

    @staticmethod
    def _header(headers, name):
        for header in headers:
            if header.get("name", "").lower() == name.lower():
                return header.get("value", "")
        return ""

    def search_messages(self, start_date=None, end_date=None):
        self._ensure_connected()

        query = [
            f"from:{self.sender}",
            f'subject:"{self.subject_contains}"',
            "has:attachment",
            "filename:pdf",
        ]

        if start_date:
            query.append(f"after:{start_date.strftime('%Y/%m/%d')}")

        if end_date:
            query.append(f"before:{end_date.strftime('%Y/%m/%d')}")

        response = (
            self.service.users()
            .messages()
            .list(
                userId="me",
                q=" ".join(query),
                maxResults=100,
            )
            .execute()
        )

        result = []

        for item in response.get("messages", []):
            message = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=item["id"],
                    format="full",
                )
                .execute()
            )

            headers = message.get("payload", {}).get("headers", [])
            received_string = self._header(headers, "Date")

            try:
                received_at = (
                    parsedate_to_datetime(received_string)
                    if received_string
                    else None
                )
            except Exception:
                received_at = None

            result.append(
                {
                    "message_id": message["id"],
                    "thread_id": message.get("threadId", ""),
                    "received_at": received_at,
                    "subject": self._header(headers, "Subject"),
                    "payload": message.get("payload", {}),
                }
            )

        return result

    def _walk_parts(self, payload):
        yield payload

        for part in payload.get("parts", []) or []:
            yield from self._walk_parts(part)

    def download_pdf_attachments(self, message):
        self._ensure_connected()

        results = []

        for part in self._walk_parts(message["payload"]):
            filename = part.get("filename", "")
            mime_type = part.get("mimeType", "")

            if not (
                filename.lower().endswith(".pdf")
                or mime_type == "application/pdf"
            ):
                continue

            body = part.get("body", {})
            data = body.get("data")
            attachment_id = body.get("attachmentId")

            if not data and attachment_id:
                attachment = (
                    self.service.users()
                    .messages()
                    .attachments()
                    .get(
                        userId="me",
                        messageId=message["message_id"],
                        id=attachment_id,
                    )
                    .execute()
                )
                data = attachment.get("data")

            if not data:
                continue

            raw = base64.urlsafe_b64decode(data.encode("utf-8"))

            safe_filename = re.sub(
                r"[^A-Za-z0-9_.-]+",
                "_",
                filename or "report.pdf",
            )

            path = (
                self.download_dir
                / f"{message['message_id']}_{safe_filename}"
            )

            path.write_bytes(raw)

            results.append(
                {
                    "message_id": message["message_id"],
                    "thread_id": message.get("thread_id", ""),
                    "received_at": message.get("received_at"),
                    "filename": safe_filename,
                    "path": str(path),
                }
            )

        return results
