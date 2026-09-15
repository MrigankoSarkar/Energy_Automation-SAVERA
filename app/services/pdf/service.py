from __future__ import annotations

from pathlib import Path
from typing import Any

from .parser import NBSensePDFParser


class PDFService:
    """
    Application service for NBSense PDF processing.
    """

    def __init__(
        self,
        parser: NBSensePDFParser | None = None,
    ) -> None:
        self.parser = parser or NBSensePDFParser()

    def parse_report(
        self,
        pdf_path: str | Path,
    ) -> dict[str, Any]:

        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(
                f"PDF file not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"PDF path is not a file: {path}"
            )

        result = self.parser.parse(path)

        # Defensive contract validation.
        readings = result.get("readings")

        if not isinstance(readings, list):
            raise TypeError(
                "PDF parser contract violation: "
                "'readings' must be a list."
            )

        return result

    def parse(
        self,
        pdf_path: str | Path,
    ) -> dict[str, Any]:
        return self.parse_report(pdf_path)

    def process(
        self,
        pdf_path: str | Path,
    ) -> dict[str, Any]:
        return self.parse_report(pdf_path)

    def extract_report(
        self,
        pdf_path: str | Path,
    ) -> dict[str, Any]:
        return self.parse_report(pdf_path)

    def extract(
        self,
        pdf_path: str | Path,
    ) -> dict[str, Any]:
        return self.parse_report(pdf_path)