from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


class GmailService:

    def __init__(self, project_dir: Path):

        self.project_dir = Path(project_dir)

        self.credentials_file = (
            self.project_dir
            / "credentials"
            / "credentials.json"
        )

        self.token_file = (
            self.project_dir
            / "credentials"
            / "token.json"
        )

    def _get_credentials(self):

        if not self.credentials_file.exists():

            raise RuntimeError(
                "GMAIL-001: Missing Google OAuth file: "
                f"{self.credentials_file}"
            )

        credentials = None

        if self.token_file.exists():

            credentials = (
                Credentials.from_authorized_user_file(
                    str(self.token_file),
                    SCOPES,
                )
            )

        if credentials:

            if credentials.expired and credentials.refresh_token:

                credentials.refresh(Request())

        if not credentials or not credentials.valid:

            flow = (
                InstalledAppFlow
                .from_client_secrets_file(
                    str(self.credentials_file),
                    SCOPES,
                )
            )

            credentials = flow.run_local_server(
                port=0,
                open_browser=True,
            )

            self.token_file.write_text(
                credentials.to_json(),
                encoding="utf-8",
            )

        return credentials

    def _service(self):

        credentials = self._get_credentials()

        return build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

    @staticmethod
    def _headers(message):

        headers = {}

        for header in (
            message
            .get("payload", {})
            .get("headers", [])
        ):

            headers[
                header["name"].lower()
            ] = header["value"]

        return headers

    def find_latest_report(
        self,
        sender: str,
        subject_contains: str,
        search_days: int = 2,
    ):

        service = self._service()

        query = (
            f"from:{sender} "
            f"newer_than:{int(search_days)}d "
            f"has:attachment "
            f'subject:"{subject_contains}"'
        )

        response = (
            service
            .users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=20,
            )
            .execute()
        )

        messages = response.get(
            "messages",
            [],
        )

        if not messages:
            return None

        candidates = []

        for message_item in messages:

            message = (
                service
                .users()
                .messages()
                .get(
                    userId="me",
                    id=message_item["id"],
                    format="full",
                )
                .execute()
            )

            headers = self._headers(message)

            internal_date = int(
                message.get(
                    "internalDate",
                    "0",
                )
            )

            candidates.append(
                (
                    internal_date,
                    message_item["id"],
                    message,
                    headers,
                )
            )

        candidates.sort(
            reverse=True,
            key=lambda item: item[0],
        )

        (
            _,
            message_id,
            message,
            headers,
        ) = candidates[0]

        return {
            "id": message_id,
            "subject": headers.get(
                "subject",
                "",
            ),
            "from": headers.get(
                "from",
                "",
            ),
            "message": message,
        }

    def download_pdf(
        self,
        report: dict,
        output_dir: Path,
    ) -> Optional[Path]:

        service = self._service()

        output_dir = Path(output_dir)

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        message_id = report["id"]

        payload = (
            report["message"]
            .get("payload", {})
        )

        pdf_attachments = []

        def walk(part):

            filename = part.get(
                "filename",
                "",
            )

            if filename.lower().endswith(".pdf"):

                pdf_attachments.append(part)

            for child in (
                part.get("parts", [])
                or []
            ):

                walk(child)

        walk(payload)

        if not pdf_attachments:

            raise RuntimeError(
                "GMAIL-002: No PDF attachment found "
                "in the report email."
            )

        attachment = pdf_attachments[0]

        filename = (
            attachment.get("filename")
            or f"nbsense_{message_id}.pdf"
        )

        attachment_id = (
            attachment
            .get("body", {})
            .get("attachmentId")
        )

        if attachment_id:

            data = (
                service
                .users()
                .messages()
                .attachments()
                .get(
                    userId="me",
                    messageId=message_id,
                    id=attachment_id,
                )
                .execute()
                .get(
                    "data",
                    "",
                )
            )

        else:

            data = (
                attachment
                .get("body", {})
                .get("data", "")
            )

        if not data:

            raise RuntimeError(
                "GMAIL-003: PDF attachment contains "
                "no data."
            )

        raw = base64.urlsafe_b64decode(
            data.encode("utf-8")
        )

        safe_filename = (
            filename
            .replace("/", "_")
            .replace("\\", "_")
        )

        destination = (
            output_dir
            / safe_filename
        )

        destination.write_bytes(raw)

        return destination