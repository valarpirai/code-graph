import io
import zipfile
from pathlib import Path

class ZipTooLargeError(Exception): pass
class InvalidZipError(Exception): pass
class ZipSlipError(Exception): pass

def extract_zip(data: io.BytesIO, dest: Path, max_bytes: int) -> None:
    """Extract zip to dest, enforcing size limit and zip-slip protection."""
    raw = data.read()
    if len(raw) > max_bytes:
        raise ZipTooLargeError(f"ZIP exceeds {max_bytes // (1024*1024)} MB limit")

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as e:
        raise InvalidZipError("Invalid or corrupt ZIP file") from e

    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()

    for member in zf.infolist():
        member_path = (dest / member.filename).resolve()
        if not str(member_path).startswith(str(dest_resolved) + "/") and member_path != dest_resolved:
            raise ZipSlipError(f"Zip-slip detected: {member.filename!r}")
        zf.extract(member, dest)
