import json
import shutil
import uuid
from pathlib import Path
from PIL import Image

from app.core.config import INPUT_DIR, WORKING_DIR, OUTPUT_DIR, EVIDENCE_DIR, DEFAULT_DPI, sanitize_filename, sanitize_job_id
from app.processors.document import normalize_to_pdf, render_pdf_to_images
from app.processors.preprocess import prepare_for_ocr, estimate_page_quality
from app.engines.vietocr_engine import ocr_image as vietocr_ocr
from app.analyzers.risk import classify_page
from app.exporters.image_pdf import images_to_image_only_pdf, verify_image_only_pdf


def resolve_unique_pdf_path(output_dir: Path, stem: str) -> Path:
    candidate = output_dir / f'{stem} (1).pdf'
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = output_dir / f'{stem} ({index}).pdf'
        if not candidate.exists():
            return candidate
        index += 1


def run_job(source_path: Path, original_name: str = None, job_id: str | None = None) -> dict:
    clean_original_name = sanitize_filename(original_name or source_path.name)
    stem = Path(clean_original_name).stem
    job_id = sanitize_job_id(job_id or stem)
    work_dir = WORKING_DIR / job_id
    input_dir = INPUT_DIR / job_id
    output_dir = OUTPUT_DIR / job_id
    evidence_dir = EVIDENCE_DIR / job_id
    for p in (work_dir, input_dir, output_dir, evidence_dir):
        p.mkdir(parents=True, exist_ok=True)

    local_input = input_dir / clean_original_name
    local_input.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, local_input)

    errors = []
    try:
        normalized_pdf = normalize_to_pdf(local_input, work_dir)
        page_images = render_pdf_to_images(normalized_pdf, work_dir / 'pages', dpi=DEFAULT_DPI)

        analyses = []
        counts = {'easy': 0, 'medium': 0, 'hard': 0}
        review_required = 0

        for idx, page_img in enumerate(page_images, start=1):
            processed = work_dir / 'ocr_pages' / page_img.name
            prepare_for_ocr(page_img, processed)
            quality = estimate_page_quality(page_img)
            regions = vietocr_ocr(processed)
            classification = classify_page(regions, quality)
            counts[classification['difficulty']] += 1
            if classification['difficulty'] == 'hard' or classification['risk_flags']:
                review_required += 1

            with Image.open(page_img) as im:
                width, height = im.size

            # Save crop evidence only for risky regions.
            risky_count = 0
            with Image.open(page_img) as original:
                for r_idx, region in enumerate(regions, start=1):
                    if not region.get('risk_flags'):
                        continue
                    risky_count += 1
                    x1, y1, x2, y2 = region['bbox']
                    pad = 8
                    crop = original.crop((max(0, x1-pad), max(0, y1-pad), min(width, x2+pad), min(height, y2+pad)))
                    crop.save(evidence_dir / f'page_{idx:04d}_region_{r_idx:04d}.png')

            analyses.append({
                'page': idx,
                'width': width,
                'height': height,
                'quality': quality,
                **classification,
                'regions': regions,
                'risky_region_count': risky_count,
            })

        out_pdf = resolve_unique_pdf_path(output_dir, stem)
        images_to_image_only_pdf(page_images, out_pdf, dpi=DEFAULT_DPI)
        pdf_verification = verify_image_only_pdf(out_pdf)
        if not pdf_verification['verified_image_only']:
            raise RuntimeError(
                f"Output PDF vẫn có text layer hoặc thiếu ảnh: embedded_text_chars={pdf_verification['embedded_text_chars']}"
            )

        evidence_json = evidence_dir / 'analysis.json'
        evidence_json.write_text(json.dumps({
            'job_id': job_id,
            'input_file': source_path.name,
            'output_type': 'IMAGE_ONLY_PDF',
            'dpi': DEFAULT_DPI,
            'pdf_verification': pdf_verification,
            'pages': analyses,
        }, ensure_ascii=False, indent=2), encoding='utf-8')

        return {
            'job_id': job_id,
            'status': 'completed',
            'input_file': source_path.name,
            'output_pdf': str(out_pdf),
            'verified_image_only': pdf_verification['verified_image_only'],
            'embedded_text_chars': pdf_verification['embedded_text_chars'],
            'pdf_verification': pdf_verification,
            'evidence_json': str(evidence_json),
            'pages': len(page_images),
            'easy_pages': counts['easy'],
            'medium_pages': counts['medium'],
            'hard_pages': counts['hard'],
            'review_required': review_required,
            'errors': errors,
        }
    except Exception as e:
        errors.append(str(e))
        return {
            'job_id': job_id,
            'status': 'failed',
            'input_file': source_path.name,
            'pages': 0,
            'easy_pages': 0,
            'medium_pages': 0,
            'hard_pages': 0,
            'review_required': 0,
            'errors': errors,
        }
