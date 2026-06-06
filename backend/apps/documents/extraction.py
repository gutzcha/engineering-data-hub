from pathlib import Path


PDF_MIME_TYPES = {"application/pdf"}
DOCX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
XLSX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def extract_text(path, mime_type: str, file_name: str) -> tuple[str, str]:
    path = Path(path)
    mime_type = (mime_type or "").lower()
    extension = path.suffix.lower() or Path(file_name).suffix.lower()

    if mime_type in PDF_MIME_TYPES or extension == ".pdf":
        return _extract_pdf(path)
    if mime_type in DOCX_MIME_TYPES or extension == ".docx":
        return _extract_docx(path)
    if mime_type in XLSX_MIME_TYPES or extension == ".xlsx":
        return _extract_xlsx(path)
    if mime_type.startswith("image/") or extension in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        return _extract_image(path)
    return "", "unsupported"


def _extract_pdf(path: Path) -> tuple[str, str]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(path)
        text = "\n".join(filter(None, (page.extract_text() or "" for page in reader.pages)))
    except Exception:
        return "", "failed"
    return text, "extracted" if text.strip() else "unsupported"


def _extract_docx(path: Path) -> tuple[str, str]:
    try:
        from docx import Document

        document = Document(path)
        parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
        for table in document.tables:
            for row in table.rows:
                parts.extend(cell.text for cell in row.cells if cell.text)
        text = "\n".join(parts)
    except Exception:
        return "", "failed"
    return text, "extracted" if text.strip() else "unsupported"


def _extract_xlsx(path: Path) -> tuple[str, str]:
    try:
        from openpyxl import load_workbook

        workbook = load_workbook(path, read_only=True, data_only=True)
        parts = []
        for sheet in workbook.worksheets:
            if sheet.sheet_state != "visible":
                continue
            parts.append(sheet.title)
            for row in sheet.iter_rows(values_only=True):
                values = [str(value) for value in row if value is not None and str(value) != ""]
                if values:
                    parts.append("\t".join(values))
        workbook.close()
        text = "\n".join(parts)
    except Exception:
        return "", "failed"
    return text, "extracted" if text.strip() else "unsupported"


def _extract_image(path: Path) -> tuple[str, str]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "", "unsupported"

    try:
        with Image.open(path) as image:
            text = pytesseract.image_to_string(image)
    except Exception:
        return "", "failed"
    return text, "extracted" if text.strip() else "unsupported"
