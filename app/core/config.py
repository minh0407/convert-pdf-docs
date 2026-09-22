from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BASE_DIR / 'storage'
INPUT_DIR = STORAGE_DIR / 'input'
WORKING_DIR = STORAGE_DIR / 'working'
OUTPUT_DIR = STORAGE_DIR / 'output'
EVIDENCE_DIR = STORAGE_DIR / 'evidence'

for p in (INPUT_DIR, WORKING_DIR, OUTPUT_DIR, EVIDENCE_DIR):
    p.mkdir(parents=True, exist_ok=True)

DEFAULT_DPI = 300
OCR_LANG = 'vie+eng'
LOCAL_HOST = '127.0.0.1'
LOCAL_PORT = 8000
import re

SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp'}


def sanitize_filename(name: str) -> str:
    if not name:
        return 'document'
    base_name = Path(name).name.strip()
    cleaned = re.sub(r'[\\/:*?"<>|]', '_', base_name)
    p = Path(cleaned)
    stem = p.stem.strip(' .')
    ext = p.suffix.strip(' .')
    if not stem:
        stem = 'document'
    if ext:
        return f"{stem}.{ext}"
    return stem


def sanitize_job_id(job_id: str) -> str:
    if not job_id:
        return 'job'
    clean = re.sub(r'[\\/:*?"<>|]', '_', str(job_id)).strip(' .')
    return clean or 'job'

