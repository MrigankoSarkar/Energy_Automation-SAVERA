import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pdf_service import process_pdf

PDF = ROOT / "data" / "pdfs" / "report_2026-09-11_2026-09-12.pdf"

EXPECTED = {
    "RASKOG NEW PANL": None,
    "Chiller Plating Plant": 141.35,
    "Main Incomer Meter": 0.00,
    "Old LT Panel Main Incomer": 3165.92,
    "Packing & Stiching Line": 477.82,
    "Rigga Line Fabrication": 179.22,
    "Press & Fabrication": 1009.43,
    "Powder Coating": 2018.03,
    "New Plating Plant": 1.21,
    "Old Plating Plant": 2.60,
    "Kaeser ASD 60 40HP Air Compressor": 776.61,
    "ELGI E18 25HP Air Compressor": 0.04,
    "ELGI E45 60HP Air Compressor": 1012.75,
    "60 HP Compressor": None,
    "DIPP_PT_PANEĹ": 0.17,
    "DUST_ COLLECTOR": 251.50,
    "SPRAY_PT_PANEL": 9.19,
    "DM Plant": 160.99,
}

def main():
    result = process_pdf(PDF)
    assert result["report_date"].isoformat() == "2026-09-12"
    assert result["page_count"] == 18
    assert len(result["meters"]) == 18

    actual = {m["meter_name"]: m["active_energy"] for m in result["meters"]}
    assert set(actual) == set(EXPECTED)

    for name, expected in EXPECTED.items():
        assert actual[name] == expected, (
            f"{name}: expected {expected}, got {actual[name]}"
        )

    print("=" * 80)
    print("PDF TEST PASSED")
    print("=" * 80)
    for m in result["meters"]:
        value = "N/A" if m["active_energy"] is None else f"{m['active_energy']:.2f} kWh"
        print(f"Page {m['page']:02d}: {m['meter_name']} -> {value}")

if __name__ == "__main__":
    main()
