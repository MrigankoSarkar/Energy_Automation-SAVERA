from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pymupdf


class PdfReportParser:

    def __init__(self, config: dict):
        self.config = config

    @staticmethod
    def _clean(value: str) -> str:

        return re.sub(
            r"\s+",
            " ",
            value,
        ).strip(
            " :\t\r\n"
        )

    @staticmethod
    def _parse_date(text: str):

        patterns = [
            r"\b(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\b",
            r"\b(\d{1,2}\s+[A-Za-z]+\s+\d{4})\b",
            r"\b(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4})\b",
            r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b",
            r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b",
        ]

        formats = [
            "%d %b %Y",
            "%d %B %Y",
            "%d-%b-%Y",
            "%d/%b/%Y",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%Y/%m/%d",
        ]

        for pattern in patterns:

            matches = re.finditer(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            for match in matches:

                raw = match.group(1).strip()

                for fmt in formats:

                    try:

                        return datetime.strptime(
                            raw,
                            fmt,
                        ).date()

                    except ValueError:
                        continue

        return None

    @classmethod
    def _extract_report_date(
        cls,
        text: str,
    ):

        # First try:
        #
        # To
        # 12 Sep 2026
        #
        direct_pattern = (
            r"\bTo\b\s*(?:Date)?\s*:?\s*"
            r"("
            r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
            r"|"
            r"\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}"
            r"|"
            r"\d{1,2}[-/]\d{1,2}[-/]\d{4}"
            r"|"
            r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
            r")"
        )

        match = re.search(
            direct_pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:

            parsed = cls._parse_date(
                match.group(1)
            )

            if parsed:
                return parsed

        # Handle PDF extraction where "To"
        # and date are separate lines.

        lines = [
            cls._clean(line)
            for line in text.splitlines()
            if cls._clean(line)
        ]

        for index, line in enumerate(lines):

            if re.fullmatch(
                r"To(?:\s+Date)?\s*:?",
                line,
                flags=re.IGNORECASE,
            ):

                for candidate in lines[
                    index + 1:index + 4
                ]:

                    parsed = cls._parse_date(
                        candidate
                    )

                    if parsed:
                        return parsed

        # Last resort:
        # select latest valid date in page.

        dates = []

        generic_pattern = (
            r"\b(?:"
            r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
            r"|"
            r"\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}"
            r"|"
            r"\d{1,2}[-/]\d{1,2}[-/]\d{4}"
            r"|"
            r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
            r")\b"
        )

        for match in re.finditer(
            generic_pattern,
            text,
            flags=re.IGNORECASE,
        ):

            parsed = cls._parse_date(
                match.group(0)
            )

            if parsed:
                dates.append(parsed)

        return max(dates) if dates else None

    def _extract_meter(self, text: str):

        lines = [
            self._clean(line)
            for line in text.splitlines()
            if self._clean(line)
        ]

        for index, line in enumerate(lines):

            if re.match(
                r"^meter\s*name\b",
                line,
                flags=re.IGNORECASE,
            ):

                value = re.sub(
                    r"^meter\s*name\s*[:\-]?\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                ).strip()

                if value:
                    return value

                if index + 1 < len(lines):
                    return lines[index + 1]

        for line in lines:

            if "meter name" in line.lower():

                value = re.split(
                    r"meter\s*name",
                    line,
                    flags=re.IGNORECASE,
                    maxsplit=1,
                )[-1]

                value = re.sub(
                    r"^[\s:=-]+",
                    "",
                    value,
                )

                if value:
                    return value

        return None

    def _extract_active_energy(
        self,
        text: str,
    ):

        unit = self.config.get(
            "pdf",
            {},
        ).get(
            "expected_unit",
            "kWh",
        )

        direct_pattern = (
            rf"active\s+energy.*?"
            rf"("
            rf"-?\d+(?:,\d{{3}})*(?:\.\d+)?"
            rf"|"
            rf"N/?A"
            rf")"
            rf"\s*{re.escape(unit)}"
        )

        direct = re.search(
            direct_pattern,
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if direct:

            raw = direct.group(1).replace(
                ",",
                "",
            )

            if (
                raw.upper()
                .replace("/", "")
                == "NA"
            ):

                return None, "N/A"

            return float(raw), "numeric"

        lines = [
            self._clean(line)
            for line in text.splitlines()
        ]

        for index, line in enumerate(lines):

            if re.search(
                r"active\s+energy",
                line,
                flags=re.IGNORECASE,
            ):

                window = " ".join(
                    lines[index:index + 10]
                )

                numeric = re.search(
                    r"("
                    r"-?\d+(?:,\d{3})*(?:\.\d+)?"
                    r")"
                    r"\s*kWh",
                    window,
                    flags=re.IGNORECASE,
                )

                if numeric:

                    return (
                        float(
                            numeric.group(1)
                            .replace(",", "")
                        ),
                        "numeric",
                    )

                if re.search(
                    r"\bN/?A\b",
                    window,
                    flags=re.IGNORECASE,
                ):

                    return None, "N/A"

        raise RuntimeError(
            "PDF-006: Active Energy value not "
            "found or is ambiguous."
        )

    def parse(self, pdf_path: Path):

        pdf_path = Path(pdf_path)

        if not pdf_path.exists():

            raise RuntimeError(
                f"PDF-001: File not found: {pdf_path}"
            )

        meters = []
        report_date = None

        with pymupdf.open(
            str(pdf_path)
        ) as document:

            if len(document) == 0:

                raise RuntimeError(
                    "PDF-002: PDF has no pages."
                )

            for page_number, page in enumerate(
                document,
                start=1,
            ):

                text = page.get_text(
                    "text"
                )

                if not text.strip():

                    raise RuntimeError(
                        f"PDF-003: Page "
                        f"{page_number} contains no "
                        f"extractable text."
                    )

                page_date = (
                    self._extract_report_date(
                        text
                    )
                )

                if (
                    report_date is None
                    and page_date
                ):

                    report_date = page_date

                meter_name = (
                    self._extract_meter(text)
                )

                if not meter_name:

                    raise RuntimeError(
                        f"PDF-004: Meter Name not "
                        f"found on page "
                        f"{page_number}."
                    )

                energy, state = (
                    self._extract_active_energy(
                        text
                    )
                )

                meters.append(
                    {
                        "page": page_number,
                        "meter_name": meter_name,
                        "active_energy": energy,
                        "state": state,
                        "unit": self.config.get(
                            "pdf",
                            {},
                        ).get(
                            "expected_unit",
                            "kWh",
                        ),
                    }
                )

        if not report_date:

            raise RuntimeError(
                "PDF-005: Report To date not found."
            )

        return {
            "report_date": report_date,
            "meters": meters,
            "page_count": len(meters),
        }