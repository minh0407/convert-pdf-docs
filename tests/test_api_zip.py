import io
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient
import pymupdf

from app.main import app

client = TestClient(app)


def test_convert_zip_endpoint():
    # 1. Prepare an in-memory ZIP containing a test PDF and a test text document (which should be skipped)
    pdf_bytes = io.BytesIO()
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 100), "Hello inside ZIP test")
    doc.save(pdf_bytes)
    doc.close()

    in_zip_bytes = io.BytesIO()
    with zipfile.ZipFile(in_zip_bytes, 'w') as zf:
        zf.writestr("DocumentA.pdf", pdf_bytes.getvalue())
        zf.writestr("DocumentB.pdf", pdf_bytes.getvalue())

    in_zip_bytes.seek(0)

    # 2. Post the ZIP file to /api/v1/convert
    response = client.post(
        "/api/v1/convert",
        files={"file": ("MyPackage.zip", in_zip_bytes, "application/zip")}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "MyPackage_converted_pdfs.zip" in response.headers.get("content-disposition", "")

    # 3. Read the returned ZIP file and verify contents
    out_zip_bytes = io.BytesIO(response.content)
    with zipfile.ZipFile(out_zip_bytes, 'r') as out_zf:
        names = out_zf.namelist()
        assert any(n.startswith("DocumentA") and n.endswith(".pdf") for n in names)
        assert any(n.startswith("DocumentB") and n.endswith(".pdf") for n in names)

        target_name = [n for n in names if n.startswith("DocumentA")][0]

        # Verify that DocumentA PDF inside ZIP is pure image
        pdf_a = out_zf.read(target_name)
        doc_check = pymupdf.open(stream=pdf_a, filetype="pdf")
        assert len(doc_check) == 1
        page = doc_check[0]
        assert len(page.get_text().strip()) == 0  # Zero text layer
        assert len(page.get_images()) >= 1       # Raster image exists
        doc_check.close()
