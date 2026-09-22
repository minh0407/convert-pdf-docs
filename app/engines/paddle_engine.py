from pathlib import Path


def available() -> bool:
    try:
        import paddleocr  # noqa
        return True
    except Exception:
        return False


def ocr_image(image_path: Path):
    """Optional CPU fallback. The MVP works without PaddleOCR installed."""
    try:
        from paddleocr import PaddleOCR
    except Exception as e:
        raise RuntimeError('PaddleOCR chưa được cài. Cài extra requirements để bật fallback này.') from e

    ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False, use_gpu=False)
    result = ocr.ocr(str(image_path), cls=True)
    regions = []
    for page in result or []:
        for item in page or []:
            box, rec = item
            text, score = rec
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            regions.append({
                'text': text,
                'confidence': float(score),
                'bbox': [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
                'engine': 'paddleocr',
                'risk_flags': []
            })
    return regions
