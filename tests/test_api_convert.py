import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

import app.api.routes as routes
from app.main import app


def test_convert_accepts_zip_and_returns_zip_of_pdfs(tmp_path, monkeypatch):
    def fake_run_job(source_path, original_name=None, job_id=None):
        stem = Path(original_name).stem if original_name else Path(source_path).stem
        job_id = job_id or stem
        output_dir = tmp_path / 'generated_output' / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        out_pdf = output_dir / f'{stem}.pdf'
        out_pdf.write_bytes(b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF')
        return {
            'job_id': job_id,
            'status': 'completed',
            'input_file': source_path.name,
            'output_pdf': str(out_pdf),
            'evidence_json': str(output_dir / 'analysis.json'),
        }

    monkeypatch.setattr(routes, 'run_job', fake_run_job)

    with TestClient(app) as client:
        input_zip = io.BytesIO()
        with zipfile.ZipFile(input_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name in ('doc_a.png', 'doc_b.png'):
                image = Image.new('RGB', (300, 400), 'white')
                draw = ImageDraw.Draw(image)
                draw.text((30, 30), name, fill='black')
                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
                zf.writestr(name, buffer.getvalue())

        response = client.post(
            '/api/v1/convert',
            files={'file': ('batch.zip', input_zip.getvalue(), 'application/zip')},
        )

        assert response.status_code == 200, response.text
        assert response.headers['content-type'].startswith('application/zip')
        assert 'converted' in response.headers['content-disposition'].lower()

        with zipfile.ZipFile(io.BytesIO(response.content)) as extracted:
            names = extracted.namelist()
            assert any(name.lower().endswith('.pdf') for name in names)
            assert len(names) >= 2
