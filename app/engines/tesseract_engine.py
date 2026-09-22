import os
import shutil
from pathlib import Path
import pytesseract
from pytesseract import Output
from PIL import Image

from app.core.config import OCR_LANG


def _find_tesseract_cmd() -> str | None:
    path = shutil.which('tesseract')
    if path:
        return path
    common_paths = [
        Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe'),
        Path(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'),
        Path(os.path.expanduser(r'~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe')),
    ]
    for p in common_paths:
        if p.exists():
            return str(p)
    return None


tess_bin = _find_tesseract_cmd()
if tess_bin:
    pytesseract.pytesseract.tesseract_cmd = tess_bin


def ocr_image(image_path: Path, lang: str = OCR_LANG):
    image = Image.open(image_path)
    try:
        data = pytesseract.image_to_data(image, lang=lang, output_type=Output.DICT, config='--oem 3 --psm 3')
    except pytesseract.TesseractNotFoundError as e:
        raise RuntimeError(
            'Không tìm thấy công cụ Tesseract OCR trên hệ thống. '
            'Vui lòng cài đặt Tesseract OCR hoặc kiểm tra biến môi trường PATH.'
        ) from e
    except Exception:
        try:
            data = pytesseract.image_to_data(image, lang='eng', output_type=Output.DICT, config='--oem 3 --psm 3')
        except Exception as exc:
            raise RuntimeError(f'Lỗi thực hiện OCR trên ảnh: {exc}') from exc
    regions = []
    n = len(data['text'])
    for i in range(n):
        txt = (data['text'][i] or '').strip()
        if not txt:
            continue
        try:
            conf = float(data['conf'][i])
        except Exception:
            conf = -1.0
        if conf < 0:
            continue
        x, y, w, h = int(data['left'][i]), int(data['top'][i]), int(data['width'][i]), int(data['height'][i])
        regions.append({
            'text': txt,
            'confidence': max(0.0, min(1.0, conf / 100.0)),
            'bbox': [x, y, x + w, y + h],
            'engine': 'tesseract',
            'risk_flags': []
        })
    return regions
