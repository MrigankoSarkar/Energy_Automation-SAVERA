# EnergyAutomation — NBSense 18-page corrected version

The supplied NBSense report has 18 pages and one meter section per page.
The parser therefore uses page-local extraction:

PAGE -> Meter Name -> Active Energy

It never globally pairs all meter names with all energy values.

Important behavior:
- N/A is None, never zero.
- Wrapped names such as Kaeser ASD 60 40HP Air Compressor are reconstructed.
- The report `To` date is used.
- Excel is updated in place.
- Only headers matching the PDF meter name are changed.
- Total is recalculated from Excel meter columns.
- The workbook is reopened and the written cells are verified.
- GUI automation runs in a background Qt thread.

Install:
    python -m pip install -r requirements.txt

PDF test:
    python tests\test_pdf.py

Gmail test:
    python tests\test_gmail.py

GUI:
    python main.py

Before production, edit config\settings.json and set the actual existing workbook path
and worksheet name.
