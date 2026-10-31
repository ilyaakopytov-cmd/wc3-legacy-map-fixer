"""Fetch the upstream CASCConsole release on first conversion (no vendored binary)."""
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import tempfile
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parent
URL = 'https://github.com/WoW-Tools/CASCExplorer/releases/download/CASCExplorer-v1.0.240/CASCConsole.zip'
ZIP_SHA256 = '005f18ddb4a90d92cc619262e67b217905144bd997ba5b0269babad29a62c439'
EXE_SHA256 = 'ebe3e3f8c880424c10cba82b9d1527d16128ef2df2cc84c9a8583db25143021e'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download() -> bytes:
    request = Request(URL, headers={'User-Agent': 'wc3-legacy-map-fixer/1.0'})
    with urlopen(request, timeout=60) as response:
        content = response.read(10_000_001)
    if len(content) > 10_000_000:
        raise ValueError('CASCConsole archive exceeds expected download size')
    return content


def ensure_casc(target: Path = ROOT / 'tools/CASCConsole') -> Path:
    """Install a pinned upstream release, without overwriting local contents."""
    target = Path(target)
    executable = target / 'CASCConsole.exe'
    if executable.exists():
        if digest(executable.read_bytes()) != EXE_SHA256:
            raise ValueError('Existing CASCConsole.exe SHA-256 mismatch')
        return executable
    if target.exists():
        raise FileExistsError(f'CASCConsole directory exists without a valid executable: {target}')
    print('Downloading CASCConsole release from WoW-Tools/CASCExplorer...')
    content = download()
    if digest(content) != ZIP_SHA256:
        raise ValueError('CASCConsole archive SHA-256 mismatch')
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        if archive.testzip():
            raise ValueError('CASCConsole archive CRC error')
        members = []
        for info in archive.infolist():
            name = info.filename
            path = PurePosixPath(name)
            if (path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name
                    or not name or name.startswith('/') or name.startswith('\\')):
                raise ValueError(f'Unsafe CASCConsole archive path: {name}')
            if not info.is_dir() and not name.lower().endswith('.pdb'):
                members.append(info)
        with tempfile.TemporaryDirectory(dir=target.parent, prefix='.casc-') as tmp:
            staging = Path(tmp) / 'CASCConsole'
            for info in members:
                path = staging.joinpath(*PurePosixPath(info.filename).parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(info))
            if not (staging / 'CASCConsole.exe').is_file() or digest((staging / 'CASCConsole.exe').read_bytes()) != EXE_SHA256:
                raise ValueError('CASCConsole.exe SHA-256 mismatch')
            os.replace(staging, target)
    return executable


if __name__ == '__main__':
    print(ensure_casc())
