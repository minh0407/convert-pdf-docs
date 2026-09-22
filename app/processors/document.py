import shutil
import subprocess
from pathlib import Path
import pymupdf
from PIL import Image

from app.core.config import DEFAULT_DPI


def _find_soffice() -> str | None:
    path = shutil.which('soffice')
    if path:
        return path
    common_paths = [
        Path(r'C:\Program Files\LibreOffice\program\soffice.exe'),
        Path(r'C:\Program Files (x86)\LibreOffice\program\soffice.exe'),
    ]
    for p in common_paths:
        if p.exists():
            return str(p)
    return None


def _convert_with_ms_word(input_path: Path, pdf_path: Path) -> bool:
    import os
    if os.name != 'nt':
        return False
    try:
        import win32com.client
        import pythoncom

        pythoncom.CoInitialize()
        word = None
        try:
            word = win32com.client.DispatchEx('Word.Application')
            word.Visible = False
            word.DisplayAlerts = 0  # wdAlertsNone
            doc = word.Documents.Open(
                str(input_path.resolve()),
                ConfirmConversions=False,
                ReadOnly=True,
                AddToRecentFiles=False,
            )
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            doc.SaveAs(str(pdf_path.resolve()), FileFormat=17)  # 17 = wdFormatPDF
            doc.Close(False)
            return pdf_path.exists()
        finally:
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
    except Exception:
        return False


def convert_office_to_pdf(input_path: Path, work_dir: Path) -> Path:
    out_dir = work_dir / 'office_pdf'
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f'{input_path.stem}.pdf'

    soffice_bin = _find_soffice()
    if soffice_bin:
        cmd = [
            soffice_bin, '--headless', '--convert-to', 'pdf', '--outdir', str(out_dir), str(input_path)
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)
            if pdf_path.exists():
                return pdf_path
        except Exception:
            pass

    if _convert_with_ms_word(input_path, pdf_path):
        return pdf_path

    raise RuntimeError(
        'Không thể chuyển đổi file Office (DOC/DOCX) sang PDF. '
        'Vui lòng cài đặt Microsoft Word hoặc LibreOffice.'
    )


def image_to_single_page_pdf_source(input_path: Path, work_dir: Path) -> Path:
    # Convert raster input to a PDF source so the rest of pipeline is uniform.
    out = work_dir / f'{input_path.stem}_source.pdf'
    img = Image.open(input_path).convert('RGB')
    img.save(out, 'PDF', resolution=DEFAULT_DPI)
    return out


def normalize_to_pdf(input_path: Path, work_dir: Path) -> Path:
    ext = input_path.suffix.lower()
    if ext == '.pdf':
        return input_path
    if ext in {'.doc', '.docx'}:
        return convert_office_to_pdf(input_path, work_dir)
    if ext in {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp'}:
        return image_to_single_page_pdf_source(input_path, work_dir)
    raise ValueError(f'Định dạng chưa hỗ trợ: {ext}')


def render_pdf_to_images(pdf_path: Path, pages_dir: Path, dpi: int = DEFAULT_DPI) -> list[Path]:
    pages_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    result: List[Path] = []
    for idx, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        out = pages_dir / f'page_{idx + 1:04d}.png'
        pix.save(out)
        result.append(out)
    doc.close()
    return result
