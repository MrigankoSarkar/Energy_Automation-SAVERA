class GmailRepository:
    """Repository/adapter boundary for Gmail operations.

    Keeps the orchestration layer independent from the Google Gmail API.
    """

    def __init__(self, gmail_service):
        self.gmail = gmail_service

    def find_reports(self, start_date=None, end_date=None):
        return self.gmail.search_messages(
            start_date=start_date,
            end_date=end_date,
        )

    def find_reports_for_date(self, target_date):
        from datetime import date, datetime, timedelta
        if isinstance(target_date, str):
            try:
                target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except Exception:
                return []
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        return self.find_reports(
            start_date=target_date,
            end_date=target_date + timedelta(days=1),
        )

    def find_reports_for_dates(self, dates):
        all_reports = []
        for d in dates:
            all_reports.extend(self.find_reports_for_date(d))
        return all_reports

    def download_reports(self, message):
        return self.gmail.download_pdf_attachments(message)

    def find_and_download_reports(self, start_date=None, end_date=None):
        artifacts = []
        for message in self.find_reports(start_date, end_date):
            artifacts.extend(self.download_reports(message))
        return artifacts
