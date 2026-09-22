import sys
import time
import argparse
import shutil
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app.core.config import SUPPORTED_EXTENSIONS, BASE_DIR
from app.core.pipeline import run_job

INPUT_DIR = BASE_DIR / 'storage' / 'auto_input'
OUTPUT_DIR = BASE_DIR / 'storage' / 'auto_output'


def process_folder(input_dir: Path, output_dir: Path):
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not files:
        return 0

    print(f"\n[+] Phát hiện {len(files)} file trong thư mục đầu vào. Bắt đầu xử lý tự động...")
    processed_count = 0

    for file_path in files:
        stem = file_path.stem
        out_pdf = output_dir / f"{stem} (1).pdf"
        print(f" -> Đang convert: {file_path.name} ...")

        try:
            res = run_job(file_path, original_name=file_path.name)
            if res.get('status') == 'completed':
                generated_pdf = Path(res['output_pdf'])
                if generated_pdf.exists():
                    shutil.copy2(generated_pdf, out_pdf)
                    print(f"    [OK] Đã tự động lưu kết quả: {out_pdf.name}")
                    file_path.unlink(missing_ok=True)
                    processed_count += 1
            else:
                print(f"    [ERROR] Thất bại: {res.get('errors')}")
        except Exception as e:
            print(f"    [ERROR] Lỗi ngoại lệ: {e}")

    return processed_count


def watch_loop(input_dir: Path, output_dir: Path, interval: int = 3):
    print(f"===========================================================")
    print(f"  HỆ THỐNG TỰ ĐỘNG CONVERT THUẦN ẢNH (AUTO-WATCHER)  ")
    print(f"===========================================================")
    print(f" Thư mục đầu vào:  {input_dir.resolve()}")
    print(f" Thư mục xuất ra:   {output_dir.resolve()}")
    print(" Chỉ cần thả các file (PDF, DOC, DOCX, Ảnh) vào thư mục đầu vào.")
    print(" Chương trình sẽ tự động convert và chuyển file PDF (1) về thư mục xuất.")
    print(" Nhấn Ctrl+C để dừng chương trình.\n")

    try:
        while True:
            process_folder(input_dir, output_dir)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[!] Đã dừng chương trình theo dõi tự động.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Tự động convert hàng loạt file PDF/DOCX sang PDF dạng scan")
    parser.add_argument("--input", type=str, default=str(INPUT_DIR), help="Thư mục chứa file đầu vào")
    parser.add_argument("--output", type=str, default=str(OUTPUT_DIR), help="Thư mục xuất file PDF kết quả")
    parser.add_argument("--watch", action="store_true", help="Chạy chế độ tự động theo dõi liên tục")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    if args.watch:
        watch_loop(in_path, out_path)
    else:
        count = process_folder(in_path, out_path)
        print(f"\n[Done] Đã xử lý xong {count} file.")
