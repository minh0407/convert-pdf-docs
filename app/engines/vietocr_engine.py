import cv2
import numpy as np
from pathlib import Path
from PIL import Image
from typing import List, Dict, Any

from vietocr.tool.config import Cfg
from vietocr.tool.predictor import Predictor

_PREDICTOR = None


def get_predictor() -> Predictor:
    global _PREDICTOR
    if _PREDICTOR is None:
        config = Cfg.load_config_from_name('vgg_transformer')
        config['device'] = 'cpu'
        config['predictor']['beamsearch'] = False
        _PREDICTOR = Predictor(config)
    return _PREDICTOR


def ocr_image(image_path: Path, **kwargs) -> List[Dict[str, Any]]:
    predictor = get_predictor()
    pil_img = Image.open(image_path).convert('RGB')
    width, height = pil_img.size

    cv_img = cv2.imread(str(image_path))
    if cv_img is None:
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel_width = max(15, width // 40)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    line_boxes = []
    min_w = 10
    min_h = 8
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w >= min_w and h >= min_h:
            line_boxes.append((x, y, w, h))

    # Sort top to bottom, then left to right
    line_boxes.sort(key=lambda b: (b[1] // 15, b[0]))

    regions = []
    for x, y, w, h in line_boxes:
        pad = 2
        crop_x1 = max(0, x - pad)
        crop_y1 = max(0, y - pad)
        crop_x2 = min(width, x + w + pad)
        crop_y2 = min(height, y + h + pad)

        crop_pil = pil_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        try:
            txt = predictor.predict(crop_pil).strip()
        except Exception:
            txt = ""

        if txt:
            regions.append({
                'text': txt,
                'confidence': 0.95,
                'bbox': [int(x), int(y), int(x + w), int(y + h)],
                'engine': 'vietocr',
                'risk_flags': []
            })

    if not regions and width > 20 and height > 20:
        try:
            txt = predictor.predict(pil_img).strip()
            if txt:
                regions.append({
                    'text': txt,
                    'confidence': 0.90,
                    'bbox': [0, 0, width, height],
                    'engine': 'vietocr',
                    'risk_flags': []
                })
        except Exception:
            pass

    return regions
