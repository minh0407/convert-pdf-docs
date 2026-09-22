import io
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.core.config import SUPPORTED_EXTENSIONS, sanitize_filename, sanitize_job_id
from app.core.pipeline import run_job
from app.exporters.image_pdf import verify_image_only_pdf

router = APIRouter(prefix='/api/v1')
JOBS = {}


def _next_unique_job_id(base_name: str, used: set[str]) -> str:
    base_name = sanitize_job_id(base_name)
    candidate = base_name
    index = 1
    while candidate in used:
        candidate = f'{base_name} ({index})'
        index += 1
    used.add(candidate)
    return candidate


async def _convert_single_file(file: UploadFile, job_id: str | None = None):
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f'Định dạng chưa hỗ trợ: {suffix}')

    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        final_job_id = job_id or _next_unique_job_id(Path(file.filename or '').stem or 'job', set(JOBS))
        result = run_job(tmp_path, original_name=file.filename, job_id=final_job_id)
        result['client_filename'] = file.filename
        JOBS[result['job_id']] = result
        return result
    finally:
        tmp_path.unlink(missing_ok=True)


async def _convert_zip_file(file: UploadFile):
    payload = await file.read()
    try:
        with zipfile.ZipFile(io.BytesIO(payload), 'r') as archive:
            supported = []
            for info in archive.infolist():
                if info.is_dir():
                    continue
                clean_name = sanitize_filename(info.filename)
                if not clean_name or clean_name.startswith('._') or '__MACOSX' in info.filename:
                    continue
                suffix = Path(clean_name).suffix.lower()
                if suffix in SUPPORTED_EXTENSIONS:
                    supported.append((info, clean_name))

            if not supported:
                raise HTTPException(status_code=400, detail='ZIP không chứa file hợp lệ để chuyển đổi PDF.')

            used_job_ids = set(JOBS)
            output_zip = NamedTemporaryFile(delete=False, suffix='.zip')
            output_zip.close()
            output_zip_path = Path(output_zip.name)

            failed_jobs = []
            completed_count = 0

            with zipfile.ZipFile(output_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as out_zip:
                for info, clean_name in supported:
                    suffix = Path(clean_name).suffix.lower()
                    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(archive.read(info.filename))
                        tmp_path = Path(tmp.name)

                    try:
                        job_id = _next_unique_job_id(Path(clean_name).stem or 'job', used_job_ids)
                        result = run_job(tmp_path, original_name=clean_name, job_id=job_id)
                        JOBS[result['job_id']] = result
                        if result.get('status') == 'completed':
                            pdf_path = Path(result['output_pdf'])
                            if pdf_path.exists():
                                out_zip.write(pdf_path, arcname=pdf_path.name)
                                completed_count += 1
                        else:
                            err_msg = ", ".join(result.get('errors', [])) or "Lỗi không xác định"
                            failed_jobs.append(f"[{clean_name}]: {err_msg}")
                    finally:
                        tmp_path.unlink(missing_ok=True)

                if failed_jobs and completed_count > 0:
                    err_report = "DANH SÁCH FILE CONVERT THẤT BẠI:\n" + "\n".join(failed_jobs)
                    out_zip.writestr("Conversion_Errors.txt", err_report)

            if completed_count == 0:
                output_zip_path.unlink(missing_ok=True)
                err_details = " | ".join(failed_jobs) if failed_jobs else "Không thể chuyển đổi các file trong ZIP."
                raise HTTPException(
                    status_code=400,
                    detail=f"Chuyển đổi thất bại: {err_details}"
                )

            return FileResponse(
                output_zip_path,
                media_type='application/zip',
                filename=f'{Path(file.filename or "converted").stem}_converted_pdfs.zip'
            )
    except HTTPException:
        raise
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail='File ZIP không hợp lệ hoặc bị hỏng.') from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Lỗi xử lý file ZIP: {str(exc)}') from exc


@router.get('/health')
def health():
    return {'status': 'ok', 'service': 'local-ocr-mvp'}


@router.post('/convert')
async def convert(file: UploadFile = File(...)):
    suffix = Path(file.filename or '').suffix.lower()
    if suffix == '.zip':
        return await _convert_zip_file(file)
    return await _convert_single_file(file)


@router.post('/convert-batch')
async def convert_batch(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail='Không có file nào được tải lên.')

    zip_path = Path(NamedTemporaryFile(delete=False, suffix='.zip').name)
    used_job_ids = set(JOBS)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            suffix = Path(file.filename or '').suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                continue

            with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(await file.read())
                tmp_path = Path(tmp.name)

            try:
                job_id = _next_unique_job_id(Path(file.filename or '').stem or 'job', used_job_ids)
                res = run_job(tmp_path, original_name=file.filename, job_id=job_id)
                JOBS[res['job_id']] = res
                if res.get('status') == 'completed':
                    out_pdf = Path(res['output_pdf'])
                    if out_pdf.exists():
                        zipf.write(out_pdf, arcname=out_pdf.name)
            finally:
                tmp_path.unlink(missing_ok=True)

    return FileResponse(
        zip_path,
        media_type='application/zip',
        filename='converted_scanned_pdfs.zip'
    )


@router.get('/jobs/{job_id}')
def job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail='Không tìm thấy job')
    return JOBS[job_id]


@router.get('/jobs/{job_id}/pdf')
def download_pdf(job_id: str):
    result = JOBS.get(job_id)
    if not result or result.get('status') != 'completed':
        raise HTTPException(status_code=404, detail='PDF chưa sẵn sàng')
    path = Path(result['output_pdf'])
    return FileResponse(path, media_type='application/pdf', filename=path.name)


@router.get('/jobs/{job_id}/verify')
def verify_pdf(job_id: str):
    result = JOBS.get(job_id)
    if not result or result.get('status') != 'completed':
        raise HTTPException(status_code=404, detail='PDF chưa sẵn sàng')
    path = Path(result['output_pdf'])
    return verify_image_only_pdf(path)


@router.get('/jobs/{job_id}/evidence')
def download_evidence(job_id: str):
    result = JOBS.get(job_id)
    if not result or result.get('status') != 'completed':
        raise HTTPException(status_code=404, detail='Evidence chưa sẵn sàng')
    path = Path(result['evidence_json'])
    return FileResponse(path, media_type='application/json', filename=path.name)
