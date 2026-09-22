from pathlib import Path
import cv2
import numpy as np


def prepare_for_ocr(image_path: Path, output_path: Path) -> Path:
    """Create an OCR-friendly copy; never alters the image used in the final PDF."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise RuntimeError(f'Không đọc được ảnh: {image_path}')
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=7)
    # Otsu improves many scans but may hurt photos; this is only the OCR copy.
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), bw)
    return output_path


def estimate_page_quality(image_path: Path) -> dict:
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return {'blur_score': 0.0, 'dark_ratio': 1.0}
    blur_score = float(cv2.Laplacian(img, cv2.CV_64F).var())
    dark_ratio = float(np.mean(img < 50))
    return {'blur_score': blur_score, 'dark_ratio': dark_ratio}
