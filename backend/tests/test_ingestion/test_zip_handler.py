import io
import zipfile
import pytest
from pathlib import Path
from app.ingestion.zip_handler import extract_zip, ZipTooLargeError, InvalidZipError, ZipSlipError

MAX_BYTES = 200 * 1024 * 1024

def make_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()

def test_extracts_files(tmp_path):
    data = make_zip({"src/Main.java": "class Main {}", "README.md": "hello"})
    dest = tmp_path / "out"
    extract_zip(io.BytesIO(data), dest, max_bytes=MAX_BYTES)
    assert (dest / "src" / "Main.java").exists()
    assert (dest / "README.md").exists()

def test_rejects_oversized(tmp_path):
    data = make_zip({"big.txt": "x" * 1000})
    dest = tmp_path / "out"
    with pytest.raises(ZipTooLargeError):
        extract_zip(io.BytesIO(data), dest, max_bytes=100)

def test_rejects_invalid_zip(tmp_path):
    dest = tmp_path / "out"
    with pytest.raises(InvalidZipError):
        extract_zip(io.BytesIO(b"not a zip file"), dest, max_bytes=MAX_BYTES)

def test_rejects_zip_slip(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../../etc/passwd", "evil")
    dest = tmp_path / "out"
    with pytest.raises(ZipSlipError):
        extract_zip(io.BytesIO(buf.getvalue()), dest, max_bytes=MAX_BYTES)

def test_rejects_absolute_path_zip_slip(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("/etc/passwd", "evil")
    dest = tmp_path / "out"
    with pytest.raises(ZipSlipError):
        extract_zip(io.BytesIO(buf.getvalue()), dest, max_bytes=MAX_BYTES)
