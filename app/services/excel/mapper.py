from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, Optional, Tuple


class ExcelMapper:
    """
    Dynamic and robust meter-to-Excel header mapper.

    Handles:
    - Whitespace variations (leading, trailing, internal multiple spaces)
    - Non-breaking spaces (\u00a0) and zero-width spaces (\u200b, \ufeff)
    - Case insensitivity
    - Punctuation and underscore variations (e.g. DUST_ COLLECTOR vs DUST COLLECTOR)
    - Unicode accent variations (e.g. DIPP_PT_PANEĹ vs DIPP_PT_PANEL)
    - Deterministic aliases
    """

    CANONICAL_ALIASES: Dict[str, str] = {
        "dipp_pt_panel": "dipp_pt_paneĺ",
        "dipp pt panel": "dipp_pt_paneĺ",
        "dipp_pt_paneĺ": "dipp_pt_paneĺ",
        "dust collector": "dust_ collector",
        "dust_collector": "dust_ collector",
        "dust_ collector": "dust_ collector",
        "kaeser asd 60 40hp air": "kaeser asd 60 40hp air compressor",
        "elgi e18 25hp air": "elgi e18 25hp air compressor",
        "elgi e45 60hp air": "elgi e45 60hp air compressor",
    }

    @staticmethod
    def normalize_text(value: Any) -> str:
        """Standard normalization for matching."""
        if value is None:
            return ""

        text = str(value)
        text = text.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")
        text = text.replace("\r", " ").replace("\n", " ")
        text = " ".join(text.split()).strip().casefold()
        return text

    @classmethod
    def strip_accents_and_punct(cls, text: str) -> str:
        """Strip accents and punctuation for fuzzy matching."""
        decomposed = unicodedata.normalize("NFKD", text)
        base = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
        cleaned = re.sub(r"[\s_\-]+", " ", base).strip().casefold()
        return cleaned

    def build_header_map(
        self,
        headers: Iterable[Any],
        start_column: int = 1,
    ) -> Dict[str, Tuple[int, str]]:
        """
        Build a header mapping dictionary.

        Maps normalized header -> (column_index, original_header_text).
        Supports both list of header strings and worksheet column enumeration.
        """
        header_map: Dict[str, Tuple[int, str]] = {}

        for index, header in enumerate(headers, start=start_column):
            if header is None:
                continue

            orig = str(header).strip()
            if not orig:
                continue

            norm = self.normalize_text(orig)
            if norm:
                header_map[norm] = (index, orig)

            simplified = self.strip_accents_and_punct(norm)
            if simplified and simplified not in header_map:
                header_map[simplified] = (index, orig)

        return header_map

    def find(
        self,
        meter_name: str,
        header_map: Dict[str, Any],
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Find a matching header for the given meter name.

        Returns (column_index, original_header_name) or (None, None).
        """
        if not meter_name:
            return None, None

        norm = self.normalize_text(meter_name)

        # 1. Direct normalized match
        if norm in header_map:
            val = header_map[norm]
            if isinstance(val, tuple):
                return val[0], val[1]
            return val, str(val)

        # 2. Alias resolution
        alias = self.CANONICAL_ALIASES.get(norm)
        if alias and alias in header_map:
            val = header_map[alias]
            if isinstance(val, tuple):
                return val[0], val[1]
            return val, str(val)

        # 3. Punctuation & accent stripped match
        simplified = self.strip_accents_and_punct(norm)
        if simplified in header_map:
            val = header_map[simplified]
            if isinstance(val, tuple):
                return val[0], val[1]
            return val, str(val)

        # 4. Check against all original headers
        for key, entry in header_map.items():
            if isinstance(entry, tuple):
                col, orig = entry
                if self.strip_accents_and_punct(orig) == simplified:
                    return col, orig

        return None, None
