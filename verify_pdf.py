import sys
from pathlib import Path
from app.exporters.image_pdf import verify_image_only_pdf

if len(sys.argv) != 2:
    print('Usage: python verify_pdf.py <file.pdf>')
    raise SystemExit(2)

path = Path(sys.argv[1])
if not path.exists():
    print(f'Không tìm thấy file: {path}')
    raise SystemExit(2)

result = verify_image_only_pdf(path)
print(f"verified_image_only: {result['verified_image_only']}")
print(f"embedded_text_chars: {result['embedded_text_chars']}")
print(f"page_count: {result['page_count']}")
for p in result['pages']:
    print(f"page {p['page']}: text_chars={p['embedded_text_chars']}, images={p['image_count']}, image_only={p['is_image_only']}")

raise SystemExit(0 if result['verified_image_only'] else 1)
