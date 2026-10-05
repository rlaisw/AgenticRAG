"""Shared fixtures: generated corpus (PDF/DOCX/XLSX/PPTX + corrupt PDF + sqlite)."""

from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture()
def corpus(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()

    from docx import Document
    d = Document()
    d.add_paragraph("Project Apollo landed humans on the Moon in 1969.")
    d.save(docs / "moon.docx")

    from pypdf import PdfWriter
    from reportlab.pdfgen import canvas  # noqa: F401 - fallback below if missing
    try:
        pdf_path = docs / "physics.pdf"
        c = canvas.Canvas(str(pdf_path))
        c.drawString(72, 720, "The speed of light in vacuum is approximately 299,792 km per second.")
        c.save()
    except ImportError:
        # minimal valid PDF with text object
        (docs / "physics.pdf").write_bytes(
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
            b"4 0 obj<</Length 90>>stream\nBT /F1 12 Tf 72 720 Td "
            b"(The speed of light in vacuum is approximately 299792 km per second.) Tj ET\n"
            b"endstream endobj\n5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000059 00000 n \n"
            b"0000000116 00000 n \n0000000241 00000 n \n0000000381 00000 n \n"
            b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n453\n%%EOF\n"
        )

    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["city", "population_m"])
    ws.append(["Tokyo", 37.4])
    ws.append(["Delhi", 32.9])
    wb.save(docs / "cities.xlsx")

    from pptx import Presentation
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Quarterly Results"
    slide.placeholders[1].text = "Revenue grew 12% year over year."
    prs.save(docs / "results.pptx")

    # corrupt file: valid extension, invalid content
    (docs / "broken.pdf").write_bytes(b"this is not a pdf")

    # sqlite source db
    db = tmp_path / "data.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    conn.execute("INSERT INTO notes (body) VALUES ('The capital of France is Paris.')")
    conn.execute("INSERT INTO notes (body) VALUES ('Water boils at 100 degrees Celsius.')")
    conn.commit()
    conn.close()

    return {"docs": docs, "db": db}
