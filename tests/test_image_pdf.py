from pathlib import Path
import pymupdf
from app.processors.document import render_pdf_to_images
from app.exporters.image_pdf import images_to_image_only_pdf, verify_image_only_pdf


def test_strict_image_only_pdf(tmp_path: Path):
    source = tmp_path / 'source.pdf'
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), 'Selectable source text 12345')
    doc.save(source)
    doc.close()

    images = render_pdf_to_images(source, tmp_path / 'pages', dpi=150)
    output = tmp_path / 'result.pdf'
    images_to_image_only_pdf(images, output, dpi=150)

    check = verify_image_only_pdf(output)
    assert check['verified_image_only'] is True
    assert check['embedded_text_chars'] == 0
    assert check['page_count'] == 1
    assert check['pages'][0]['image_count'] >= 1


def test_docx_conversion_pipeline(tmp_path: Path):
    from app.core.pipeline import run_job
    docx_file = tmp_path / 'sample.docx'
    
    # Create docx via MS Word if installed
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        doc = word.Documents.Add()
        doc.Range(0, 0).Text = "Test Docx Content for Pipeline"
        doc.SaveAs(str(docx_file.resolve()), FileFormat=16)
        doc.Close(False)
        word.Quit()
        pythoncom.CoUninitialize()
    except Exception:
        return  # Skip test if MS Word environment is not available

    res = run_job(docx_file)
    assert res['status'] == 'completed'
    assert res['verified_image_only'] is True
    assert res['embedded_text_chars'] == 0

