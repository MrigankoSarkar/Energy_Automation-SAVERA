import traceback

def classify_error(message):
    text = str(message)
    for prefix, category in (
        ("GMAIL-", "GMAIL"),
        ("PDF-", "PDF"),
        ("EXCEL-", "EXCEL"),
        ("CONFIG-", "CONFIG"),
    ):
        if text.startswith(prefix):
            return category
    return "SYSTEM"

def get_error_details(exc):
    return {
        "category": classify_error(exc),
        "message": str(exc),
        "traceback": traceback.format_exc()
    }
