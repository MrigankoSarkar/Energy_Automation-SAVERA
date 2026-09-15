from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pymupdf


class NBSensePDFParser:
    """
    Parser for NBSense EMS Monitoring Report PDFs.

    Contract:
        parse() -> {
            "report_date": datetime,
            "report_date_iso": "YYYY-MM-DD",
            "meters": list[dict],
            "readings": list[dict],
            "reading_lookup": dict[str, dict],
            "meter_count": int,
            "source_file": str,
        }

    Important:
    - readings is ALWAYS a list.
    - N/A is represented as status="N/A", value=None.
    - N/A is NOT converted to zero.
    - Numeric values are normalized to kWh.
    - Pages are parsed independently.
    """

    DATE_RE = re.compile(
        r"\b(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+(\d{4})\b",
        re.IGNORECASE,
    )

    NUMERIC_ENERGY_RE = re.compile(
        r"([-+]?\d+(?:\.\d+)?)\s*(kWh|MWh)\b",
        re.IGNORECASE,
    )

    NA_ENERGY_RE = re.compile(
        r"\b(?:N/?A|N\.?A\.?|NOT\s+AVAILABLE)"
        r"(?:\s*(kWh|MWh))?\b",
        re.IGNORECASE,
    )

    METER_LABEL_RE = re.compile(
        r"^\s*Meter\s*Name\s*:?\s*(.*)$",
        re.IGNORECASE,
    )

    STOP_LABELS = {
        "from",
        "to",
        "total energy consumption",
        "active energy",
        "reactive energy",
        "apparent energy",
        "power factor",
        "maximum demand",
        "minimum demand",
        "average demand",
        "energy consumption",
        "report",
        "date",
        "avg pf",
        "average pf",
        "avg. pf",
        "parameter name",
        "min value",
        "max value",
        "avg value",
        "voltage ry",
        "voltage yb",
        "voltage rb",
        "current r",
        "current y",
        "current b",
        "active power",
        "apparent power",
    }

    # Deterministic corrections for known NBSense meter-name truncation/encoding.
    METER_ALIASES = {
        "kaeser asd 60 40hp air": "Kaeser ASD 60 40HP Air Compressor",
        "kaeser asd 60 40hp air compressor":
            "Kaeser ASD 60 40HP Air Compressor",

        "elgi e18 25hp air": "ELGI E18 25HP Air Compressor",
        "elgi e18 25hp air compressor":
            "ELGI E18 25HP Air Compressor",

        "elgi e45 60hp air": "ELGI E45 60HP Air Compressor",
        "elgi e45 60hp air compressor":
            "ELGI E45 60HP Air Compressor",

        "dipp_pt_panel": "DIPP_PT_PANEĹ",
        "dipp_pt_paneĺ": "DIPP_PT_PANEĹ",
    }

    def parse(self, pdf_path: str | Path) -> dict[str, Any]:
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        if not path.is_file():
            raise ValueError(f"PDF path is not a file: {path}")

        pages: list[dict[str, Any]] = []

        with pymupdf.open(path) as document:
            if len(document) == 0:
                raise ValueError("PDF contains no pages.")

            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text") or ""

                parsed_page = self._parse_page(
                    text=text,
                    page_number=page_number,
                )

                pages.append(parsed_page)

        if not pages:
            raise ValueError("No EMS report pages could be parsed.")

        report_date = self._resolve_report_date(pages)

        # IMPORTANT:
        # readings MUST be a LIST for compatibility with the workflow.
        readings: list[dict[str, Any]] = []

        for item in pages:
            readings.append(
                {
                    "meter_name": item["meter_name"],
                    "value": item["active_energy"],
                    "unit": item["unit"],
                    "status": item["status"],
                    "page": item["page"],
                }
            )

        # Optional lookup structure for components that want O(1) access.
        reading_lookup: dict[str, dict[str, Any]] = {}

        for reading in readings:
            meter_name = reading["meter_name"]
            normalized = self.normalize_meter_name(meter_name)

            if normalized in reading_lookup:
                raise ValueError(
                    f"Duplicate meter detected in PDF: {meter_name}"
                )

            reading_lookup[normalized] = reading

        return {
            "report_date": report_date,
            "report_date_iso": report_date.strftime("%Y-%m-%d"),
            "meters": pages,
            "readings": readings,
            "reading_lookup": reading_lookup,
            "meter_count": len(pages),
            "source_file": str(path),
        }

    def parse_report(self, pdf_path: str | Path) -> dict[str, Any]:
        return self.parse(pdf_path)

    def extract(self, pdf_path: str | Path) -> dict[str, Any]:
        return self.parse(pdf_path)

    def extract_report(self, pdf_path: str | Path) -> dict[str, Any]:
        return self.parse(pdf_path)

    def process(self, pdf_path: str | Path) -> dict[str, Any]:
        return self.parse(pdf_path)

    # ------------------------------------------------------------------
    # Page parsing
    # ------------------------------------------------------------------

    def _parse_page(
        self,
        text: str,
        page_number: int,
    ) -> dict[str, Any]:

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        if not lines:
            raise ValueError(
                f"Page {page_number}: page contains no readable text."
            )

        meter_name = self._extract_meter_name(lines)

        if not meter_name:
            raise ValueError(
                f"Page {page_number}: Meter Name could not be extracted."
            )

        report_date = self._extract_to_date(lines)

        active_energy, unit, status = self._extract_active_energy(lines)

        if status not in {"VALID", "N/A"}:
            status = "MISSING"

        return {
            "page": page_number,
            "meter_name": meter_name,
            "active_energy": active_energy,
            "unit": unit,
            "status": status,
            "report_date": report_date,
        }

    # ------------------------------------------------------------------
    # Meter name
    # ------------------------------------------------------------------

    def _extract_meter_name(self, lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            match = self.METER_LABEL_RE.match(line)

            if not match:
                continue

            meter_name = match.group(1).strip()

            # Handle:
            #
            # Meter Name : Kaeser ASD 60 40HP Air
            # Compressor
            #
            # where NBSense wraps the meter name.
            continuation_parts: list[str] = []

            if index + 1 < len(lines):
                next_line = lines[index + 1].strip()

                if self._looks_like_meter_continuation(next_line):
                    continuation_parts.append(next_line)

            if continuation_parts:
                meter_name = " ".join(
                    [meter_name] + continuation_parts
                ).strip()

            if not meter_name and index + 1 < len(lines):
                candidate = lines[index + 1].strip()

                if self._looks_like_meter_continuation(candidate):
                    meter_name = candidate

            if meter_name:
                return self._canonical_meter_name(meter_name)

        # Fallback for PDFs where "Meter Name" and value are separate lines.
        for index, line in enumerate(lines):
            if line.strip().casefold() == "meter name":
                if index + 1 < len(lines):
                    candidate = lines[index + 1].strip()

                    if candidate:
                        return self._canonical_meter_name(candidate)

        return None

    def _looks_like_meter_continuation(self, line: str) -> bool:
        if not line:
            return False

        normalized = line.casefold().strip()

        if normalized in self.STOP_LABELS:
            return False

        if self.DATE_RE.search(line):
            return False

        if self.NUMERIC_ENERGY_RE.search(line):
            return False

        if self.NA_ENERGY_RE.search(line):
            return False

        # Do not consume obvious report metadata.
        metadata_prefixes = (
            "from",
            "to",
            "total ",
            "active ",
            "reactive ",
            "apparent ",
            "power ",
            "energy ",
            "savera ",
            "avg",
            "average",
            "min",
            "max",
            "parameter",
            "voltage",
            "current",
        )

        if any(normalized.startswith(prefix) for prefix in metadata_prefixes):
            return False

        return True

    def _canonical_meter_name(self, name: str) -> str:
        cleaned = re.sub(r"\s+", " ", name).strip()

        normalized = self.normalize_meter_name(cleaned)

        return self.METER_ALIASES.get(
            normalized,
            cleaned,
        )

    # ------------------------------------------------------------------
    # Date
    # ------------------------------------------------------------------

    def _extract_to_date(self, lines: list[str]) -> datetime | None:

        for index, line in enumerate(lines):

            if line.casefold() == "to":
                # NBSense format:
                #
                # To
                # 12 Sep 2026
                if index + 1 < len(lines):
                    match = self.DATE_RE.search(lines[index + 1])

                    if match:
                        return self._parse_date_match(match)

            # Same-line fallback:
            #
            # To 12 Sep 2026
            if line.casefold().startswith("to "):
                match = self.DATE_RE.search(line)

                if match:
                    return self._parse_date_match(match)

        # Last fallback: find a report date anywhere on page.
        for line in lines:
            match = self.DATE_RE.search(line)

            if match:
                return self._parse_date_match(match)

        return None

    def _parse_date_match(self, match: re.Match) -> datetime:
        day = int(match.group(1))
        month = match.group(2).title()
        year = int(match.group(3))

        return datetime.strptime(
            f"{day} {month} {year}",
            "%d %b %Y",
        )

    # ------------------------------------------------------------------
    # Active Energy
    # ------------------------------------------------------------------

    def _extract_active_energy(
        self,
        lines: list[str],
    ) -> tuple[float | None, str | None, str]:

        for index, line in enumerate(lines):

            normalized = line.casefold().strip()

            if normalized == "active energy":

                # Usually the next line contains:
                #
                # 776.61 kWh
                #
                # or:
                #
                # N/A kWh

                if index + 1 < len(lines):
                    candidate = lines[index + 1].strip()

                    value, unit, status = self._parse_energy_value(
                        candidate
                    )

                    if status in {"VALID", "N/A"}:
                        return value, unit, status

                # Same-line fallback.
                value, unit, status = self._parse_energy_value(line)

                if status in {"VALID", "N/A"}:
                    return value, unit, status

        # Search whole page as fallback.
        for line in lines:
            value, unit, status = self._parse_energy_value(line)

            if status in {"VALID", "N/A"}:
                return value, unit, status

        return None, None, "MISSING"

    def _parse_energy_value(
        self,
        text: str,
    ) -> tuple[float | None, str | None, str]:

        # NBSense commonly produces:
        #
        # N/A kWh
        #
        # This MUST remain N/A and MUST NOT become zero.
        na_match = self.NA_ENERGY_RE.search(text)

        if na_match:
            unit = na_match.group(1)

            if unit:
                unit = unit.lower()

            return None, unit, "N/A"

        numeric_match = self.NUMERIC_ENERGY_RE.search(text)

        if not numeric_match:
            return None, None, "MISSING"

        raw_value = float(numeric_match.group(1))
        unit = numeric_match.group(2).lower()

        # Normalize all energy values to kWh.
        if unit == "mwh":
            raw_value *= 1000.0
            unit = "kwh"

        return raw_value, unit, "VALID"

    # ------------------------------------------------------------------
    # Report date consistency
    # ------------------------------------------------------------------

    def _resolve_report_date(
        self,
        pages: list[dict[str, Any]],
    ) -> datetime:

        dates = [
            item["report_date"]
            for item in pages
            if item.get("report_date") is not None
        ]

        if not dates:
            raise ValueError(
                "Could not determine report date from PDF."
            )

        first_date = dates[0]

        for date_value in dates[1:]:
            if date_value.date() != first_date.date():
                raise ValueError(
                    "Inconsistent report dates detected across PDF pages: "
                    f"{first_date.date()} and {date_value.date()}."
                )

        return first_date

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_meter_name(name: str) -> str:
        value = str(name or "").strip().casefold()

        # Normalize Unicode apostrophe/accent variations where practical.
        value = value.replace("’", "'")
        value = value.replace("`", "'")

        # Normalize whitespace.
        value = re.sub(r"\s+", " ", value)

        return value.strip()


# Backward-compatible aliases.
PDFParser = NBSensePDFParser
NbsensePDFParser = NBSensePDFParser


def normalize_meter_name(name: str) -> str:
    """Module-level helper to normalize meter names."""
    return NBSensePDFParser.normalize_meter_name(name)


def parse_date(date_str: str) -> datetime:
    """Module-level helper to parse date strings."""
    match = NBSensePDFParser.DATE_RE.search(str(date_str))
    if match:
        day = int(match.group(1))
        month = match.group(2).title()
        year = int(match.group(3))
        return datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except ValueError:
            pass
    raise ValueError(f"Could not parse date: {date_str}")