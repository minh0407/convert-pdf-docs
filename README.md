# Local OCR MVP — Image-only PDF

MVP OCR chạy local cho Windows/Linux, nhận PDF/DOC/DOCX/ảnh và xuất **PDF chỉ chứa ảnh raster**, vì vậy không có searchable text layer và không thể bôi đen/copy chữ từ lớp text PDF.

## Mục tiêu

- Local API chỉ bind `127.0.0.1:8000`.
- Local API chỉ bind `127.0.0.1:8000`.
- OCR hậu trường bằng VietOCR (Vietnamese Transformer OCR) + OpenCV Layout Line Detection.
- Giữ nguyên trang gốc trong PDF đầu ra; ảnh/bảng/chữ ký/dấu vẫn nằm trong ảnh trang.
- OCR copy được preprocess riêng, không làm thay đổi ảnh dùng tạo PDF cuối.
- Evidence: JSON theo trang + crop ảnh ở vùng có rủi ro.
- Phân loại page: `easy`, `medium`, `hard`.
- Có điểm mở rộng PaddleOCR và OpenAI/Gemini fallback ở phase sau.

## 1. Phần mềm cần cài

### Python
Khuyến nghị Python 3.12.

### VietOCR & PyTorch
VietOCR và PyTorch CPU tự động được cài đặt qua `requirements.txt`.

### LibreOffice
Chỉ cần nếu xử lý `.doc` / `.docx`. Đảm bảo `soffice` nằm trong PATH.

Kiểm tra:

```powershell
soffice --version
```

## 2. Cài project

Windows PowerShell:

```powershell
cd local_ocr_mvp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Chạy

```powershell
python run.py
```

API:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## 4. API

### Health

```http
GET /api/v1/health
```

### Convert

```http
POST /api/v1/convert
Content-Type: multipart/form-data
file=<document>
```

Ví dụ curl:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/convert" -F "file=@D:\docs\hopdong.pdf"
```

Response chứa `job_id`, số trang easy/medium/hard, đường dẫn output và evidence.

### Lấy PDF

```http
GET /api/v1/jobs/{job_id}/pdf
```

### Lấy evidence JSON

```http
GET /api/v1/jobs/{job_id}/evidence
```

## 5. Evidence và case khó

Các vùng có confidence thấp / ký tự đặc biệt / scan mờ được lưu crop trong:

```text
storage/evidence/<job_id>/
```

`analysis.json` chứa:

- page
- bbox
- recognized text
- confidence
- engine
- risk flags
- page difficulty
- blur score

### Một số risk flag hiện có

- `LOW_CONFIDENCE`
- `MEDIUM_CONFIDENCE`
- `SPECIAL_SYMBOL`
- `ALPHANUMERIC_AMBIGUITY`
- `BLURRY_SCAN`
- `DARK_BACKGROUND`
- `NO_TEXT_DETECTED`

## 6. Case matrix của MVP

| Case | Mức | MVP |
|---|---|---|
| PDF scan rõ, Việt/Anh | Dễ | Có |
| PDF có text layer | Dễ | Raster hóa rồi OCR |
| DOC/DOCX chuẩn | Dễ | Có qua LibreOffice |
| Ảnh trong tài liệu | Dễ | Giữ nguyên trong page image |
| Bảng rõ đường kẻ | Trung bình | OCR chữ, chưa dựng cell structure |
| Bảng merged-cell / không viền | Khó | Phase PaddleOCR |
| Dấu đỏ đè chữ | Khó | Có thể flag confidence; cần benchmark |
| Ký tự ± ≤ ≥ Ω µ Ø | Khó | Có risk flag |
| Công thức toán | Khó | Chưa chuyên dụng |
| Chữ viết tay | Rất khó | Chưa chuyên dụng |
| Chữ bị che/mất khỏi ảnh | Không thể chắc chắn | Chỉ flag/review |

## 7. Lưu ý quan trọng

PDF đầu ra được dựng lại từ ảnh trang. Vì vậy OCR **không được nhúng** vào PDF đầu ra. Nếu một PDF viewer vẫn có tính năng OCR riêng của ứng dụng, viewer có thể tự nhận dạng chữ khi người dùng yêu cầu; đó không phải text layer do chương trình tạo.

## 8. Phase tiếp theo

1. PaddleOCR/PP-Structure cho table/layout phức tạp.
2. So sánh hai OCR engine để phát hiện disagreement.
3. OpenAI/Gemini fallback chỉ gửi crop vùng khó, mặc định tắt.
4. Benchmark CER/WER/table accuracy trên bộ tài liệu thực tế.
5. Background job queue cho file lớn.

## v0.2 - Strict image-only verification

The exporter now creates a brand-new PDF and inserts one full-page raster image per page. It never copies source PDF objects or OCR text.

Every successful job is verified before the API returns `completed`:

- `verified_image_only: true`
- `embedded_text_chars: 0`
- every page has at least one embedded raster image

You can verify any result manually:

```bat
python verify_pdf.py "D:\path\to\result_scan.pdf"
```

Or via API:

```text
GET /api/v1/jobs/{job_id}/verify
```

Important: Edge, Chrome, Adobe Acrobat and other PDF viewers may run their own OCR on an image-only PDF. That can make text selectable in the viewer even when the PDF file itself has no text layer. `verify_pdf.py` checks the actual PDF content.
