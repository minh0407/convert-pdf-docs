from pathlib import Path
from typing import List, Dict, Any
import pymupdf


def images_to_image_only_pdf(page_images: List[Path], output_pdf: Path, dpi: int = 300) -> Path:
    """Build a brand-new PDF whose page content is raster images only.

    No source PDF objects are copied. No OCR text is embedded.
    Each output page contains exactly one full-page raster image.
    """
    if not page_images:
        raise ValueError('Không có trang ảnh để tạo PDF.')

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    try:
        for image_path in page_images:
            pix = pymupdf.Pixmap(str(image_path))
            # Convert pixel dimensions to PDF points while preserving the selected DPI.
            width_pt = pix.width * 72.0 / dpi
            height_pt = pix.height * 72.0 / dpi
            page = doc.new_page(width=width_pt, height=height_pt)
            page.insert_image(page.rect, filename=str(image_path), keep_proportion=False)
            pix = None

        # garbage=4 and deflate clean/compress the newly created image-only PDF.
        doc.save(str(output_pdf), garbage=4, deflate=True)
    finally:
        doc.close()

    return output_pdf


def verify_image_only_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Verify that the PDF contains no embedded/extractable text.

    Note: some viewers (Edge/Chrome/Adobe) may perform *viewer-side OCR* and let
    users select text even when the PDF itself contains zero text objects.
    This function checks the actual PDF content, not viewer behavior.
    """
    doc = pymupdf.open(str(pdf_path))
    pages = []
    total_text_chars = 0
    all_pages_have_images = True

    try:
        for index in range(1, doc.page_count + 1):
            page = doc.load_page(index - 1)
            extracted = page.get_text('text')
            extracted_text = extracted if isinstance(extracted, str) else ''
            text_chars = len(extracted_text.strip())
            images = page.get_images(full=True)
            image_count = len(images)
            total_text_chars += text_chars
            if image_count < 1:
                all_pages_have_images = False
            pages.append({
                'page': index,
                'embedded_text_chars': text_chars,
                'image_count': image_count,
                'is_image_only': text_chars == 0 and image_count >= 1,
            })
    finally:
        doc.close()

    verified = total_text_chars == 0 and all_pages_have_images and bool(pages)
    return {
        'verified_image_only': verified,
        'embedded_text_chars': total_text_chars,
        'page_count': len(pages),
        'all_pages_have_images': all_pages_have_images,
        'pages': pages,
    }
