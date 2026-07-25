from uuid import uuid4

import fitz

from contexthub.infrastructure.parsers.pymupdf_parser import PyMuPDFDocumentParser


def test_pdf_parser_preserves_one_based_pages_and_empty_pages(tmp_path) -> None:  # type: ignore[no-untyped-def]
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page_one = document.new_page()
    page_one.insert_text((72, 72), "Hello from page one")
    document.new_page()
    document.save(pdf_path)
    document.close()

    parsed = PyMuPDFDocumentParser().parse(pdf_path, uuid4())

    assert [page.page_number for page in parsed.pages] == [1, 2]
    assert "Hello from page one" in parsed.pages[0].text
    assert parsed.pages[1].text == ""
