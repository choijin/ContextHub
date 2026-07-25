"""PyMuPDF document parser."""

from pathlib import Path
from uuid import UUID

from contexthub.domain.exceptions import DocumentParsingError
from contexthub.domain.models.document import DocumentPage, NormalizedDocument


class PyMuPDFDocumentParser:
    """Parse PDFs into page-aware domain models."""

    def parse(self, file_path: Path, document_id: UUID) -> NormalizedDocument:
        if not file_path.exists():
            raise DocumentParsingError("PDF file does not exist.")
        if file_path.suffix.lower() != ".pdf":
            raise DocumentParsingError("Document parser only accepts PDF files.")

        try:
            import fitz  # type: ignore[import-untyped]
        except ImportError as exc:
            raise DocumentParsingError("PyMuPDF is not installed.") from exc

        try:
            with fitz.open(file_path) as pdf:
                pages = [
                    DocumentPage(
                        document_id=document_id,
                        page_number=page_index + 1,
                        text=self._normalize_text(page.get_text("text")),
                    )
                    for page_index, page in enumerate(pdf)
                ]
        except Exception as exc:
            raise DocumentParsingError("Failed to parse PDF document.") from exc

        return NormalizedDocument(document_id=document_id, pages=pages)

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [" ".join(line.split()) for line in normalized.split("\n")]
        return "\n".join(lines).strip()
