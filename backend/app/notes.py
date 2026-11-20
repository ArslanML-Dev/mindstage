"""Turn an uploaded file into plain text (text, .docx, text PDFs; photos/scanned PDFs via the AI)."""
import io

from . import ai

MAX_BYTES = 10 * 1024 * 1024
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


class NotesError(Exception):
    pass


def extract_text(filename: str, data: bytes) -> str:
    if not data:
        raise NotesError("The uploaded file is empty.")
    if len(data) > MAX_BYTES:
        raise NotesError("File is too big — upload something under 10 MB.")
    name = (filename or "").lower()
    ext = name[name.rfind("."):] if "." in name else ""
    if ext in (".txt", ".md"):
        return data.decode("utf-8", errors="ignore")
    if ext == ".docx":
        from docx import Document
        try:
            doc = Document(io.BytesIO(data))
        except Exception as e:
            raise NotesError("Could not open that Word file.") from e
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            parts += [" | ".join(c.text.strip() for c in row.cells) for row in table.rows]
        return "\n".join(parts)
    if ext == ".pdf":
        from pypdf import PdfReader
        try:
            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages[:40])
        except Exception as e:
            raise NotesError("Could not open that PDF.") from e
        if len(text.strip()) >= 50:
            return text
        return ai.transcribe(data, "application/pdf")  # scanned PDF
    if ext in IMAGE_TYPES:
        return ai.transcribe(data, IMAGE_TYPES[ext])
    raise NotesError("Upload a PDF, Word (.docx), text file, or a photo (JPG/PNG) of your notes.")
