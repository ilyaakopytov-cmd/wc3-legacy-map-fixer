"""Apply and structurally verify A-SKIN on a separate Warcraft III map copy."""
import argparse
from collections import Counter
import ctypes as c
import hashlib
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile

from tools.compat_patch import parse_slk, build_skin
from tools.mpq import _archive, _functions, read_entry
from setup_casc import ensure_casc

ROOT = Path(__file__).resolve().parent
CASC_EXE = ROOT / 'tools/CASCConsole/CASCConsole.exe'
CASC_SHA256 = 'ebe3e3f8c880424c10cba82b9d1527d16128ef2df2cc84c9a8583db25143021e'
PROTECTED_HEADER = 0x504f7856
METADATA = {'(listfile)', '(attributes)'}
UNIT_SKIN = r'Units\UnitSkin.txt'
ITEM_SKIN = r'Units\ItemSkin.txt'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _remove_owned(path: Path, identity: os.stat_result) -> bool:
    """Only remove the file this process created, never a competing replacement."""
    try:
        current = path.lstat()
    except FileNotFoundError:
        return False
    if (stat.S_ISREG(current.st_mode) and
            (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino)):
        path.unlink()
        return True
    return False


def _write_exclusive(path: Path, content: bytes | Path) -> os.stat_result:
    """Stage on the destination volume, then publish without replacing it."""
    fd, filename = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.stage-')
    staged = Path(filename)
    try:
        with os.fdopen(fd, 'wb') as destination:
            identity = os.fstat(destination.fileno())
            if isinstance(content, Path):
                with content.open('rb') as source:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
            else:
                destination.write(content)
        # Windows os.rename is atomic on one volume and refuses an existing target.
        os.rename(staged, path)
        return identity
    finally:
        staged.unlink(missing_ok=True)


def extract_client_skins(game: Path, destination: Path) -> Path:
    """Extract current Classic Skin definitions from the installed client."""
    if not (game / 'Data').is_dir():
        raise FileNotFoundError(f'Game Data directory not found: {game}')
    ensure_casc()
    if not CASC_EXE.is_file() or sha(CASC_EXE.read_bytes()) != CASC_SHA256:
        raise ValueError('CASCConsole.exe missing or SHA-256 mismatch')
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        paths = Path(temporary) / 'paths.txt'
        paths.write_text('war3.w3mod/units/unitskin.txt\nwar3.w3mod/units/itemskin.txt\n', encoding='ascii')
        cmd = [str(CASC_EXE), '-m', 'Listfile', '-e', str(paths), '-d', str(destination),
               '-l', 'ruRU', '-p', 'w3', '-s', str(game)]
        completed = subprocess.run(cmd, cwd=CASC_EXE.parent, capture_output=True,
                                   text=True, errors='replace', timeout=120)
        if completed.returncode or completed.stdout.count(' Ok!') < 2:
            raise RuntimeError('Client Skin extraction failed: ' + (completed.stdout + completed.stderr)[-1200:])
    extracted = destination / 'war3.w3mod/units'
    for name in ('unitskin.txt', 'itemskin.txt'):
        data = (extracted / name).read_bytes()
        if b'[Hamg]' not in data and name == 'unitskin.txt':
            raise ValueError('Client UnitSkin data is not plausible')
        if len(data) < 1000:
            raise ValueError(f'Client Skin data too short: {name}')
    return extracted


class FindData(c.Structure):
    _fields_ = [('name', c.c_char * 260), ('plain', c.c_void_p), ('hash_index', c.c_uint32),
                ('block_index', c.c_uint32), ('size', c.c_uint32), ('flags', c.c_uint32),
                ('compressed_size', c.c_uint32), ('time_lo', c.c_uint32),
                ('time_hi', c.c_uint32), ('locale', c.c_uint32)]


def _advance_find(next_file, handle, found) -> bool:
    if next_file(handle, c.byref(found)):
        return True
    error = c.get_last_error()
    if error != 18:  # ERROR_NO_MORE_FILES
        raise OSError(error, 'MPQ enumeration failed')
    return False


def archive_snapshot(path: Path) -> Counter:
    """Read every enumerated MPQ payload; fail closed on unreadable files."""
    lib = _functions()
    open_file, close_file, size_file, read_file = lib[2:6]
    dll = c.WinDLL(str(ROOT / 'tools/StormLib.dll'), use_last_error=True)
    first = dll.SFileFindFirstFile
    first.argtypes = [c.c_void_p, c.c_char_p, c.POINTER(FindData), c.c_wchar_p]
    first.restype = c.c_void_p
    next_file = dll.SFileFindNextFile
    next_file.argtypes = [c.c_void_p, c.POINTER(FindData)]
    next_file.restype = c.c_bool
    close_find = dll.SFileFindClose
    close_find.argtypes = [c.c_void_p]
    close_find.restype = c.c_bool
    set_locale = dll.SFileSetLocale
    set_locale.argtypes = [c.c_uint32]
    set_locale.restype = c.c_uint32
    get_info = dll.SFileGetFileInfo
    get_info.argtypes = [c.c_void_p, c.c_uint32, c.c_void_p, c.c_uint32, c.c_void_p]
    get_info.restype = c.c_bool
    records = Counter()
    with _archive(path) as archive:
        found = FindData()
        handle = first(archive, b'*', c.byref(found), None)
        if not handle:
            raise OSError(c.get_last_error(), 'Cannot enumerate MPQ')
        original_locale = dll.SFileGetLocale()
        try:
            while True:
                name = bytes(found.name).split(b'\0')[0]
                file_handle = c.c_void_p()
                set_locale(found.locale)
                if not open_file(archive, name, 0, c.byref(file_handle)):
                    raise OSError(c.get_last_error(), f'Cannot open MPQ entry {name!r}')
                try:
                    for info_class, expected in ((43, found.hash_index), (47, found.locale)):
                        actual = c.c_uint32()
                        if not get_info(file_handle, info_class, c.byref(actual), c.sizeof(actual), None):
                            raise OSError(c.get_last_error(), f'Cannot check MPQ entry identity {name!r}')
                        if actual.value != expected:
                            raise ValueError(f'MPQ entry identity mismatch: {name!r}')
                    size = size_file(file_handle, None)
                    if size == 0xFFFFFFFF or size > 64_000_000:
                        raise ValueError(f'Unexpected entry size: {name!r} ({size})')
                    buffer = c.create_string_buffer(size)
                    got = c.c_uint32()
                    if not read_file(file_handle, buffer, size, c.byref(got), None) or got.value != size:
                        raise OSError(c.get_last_error(), f'Cannot read MPQ entry {name!r}')
                    records[(name.decode('utf-8', errors='replace').lower(), found.locale, size,
                             sha(buffer.raw[:size]))] += 1
                finally:
                    close_file(file_handle)
                if not _advance_find(next_file, handle, found):
                    break
        finally:
            set_locale(original_locale)
            close_find(handle)
    return records


def _source_layout(data: bytes) -> tuple[int, int]:
    offset = 512 if data[:4] == b'HM3W' and data[512:516] == b'MPQ\x1a' else 0
    if data[offset:offset+4] != b'MPQ\x1a':
        raise ValueError('Unsupported map: no recognized MPQ header')
    header = struct.unpack_from('<I', data, offset + 4)[0]
    if header not in (32, PROTECTED_HEADER):
        raise ValueError(f'Unsupported MPQ header size: {header:#x}')
    return offset, header


def _has_entry(source: Path, name: str) -> bool:
    try:
        read_entry(source, name)
    except FileNotFoundError:
        return False
    return True


def run(source: Path, *, output: Path | None = None, report: Path | None = None,
        client_dir: Path | None = None,
        game: Path | None = None) -> dict:
    source = source.resolve()
    if not source.is_file() or source.suffix.lower() not in ('.w3x', '.w3m'):
        raise ValueError(f'Expected an existing Warcraft III map: {source}')
    raw = source.read_bytes()
    before_hash = sha(raw)
    offset, header = _source_layout(raw)
    for name in (UNIT_SKIN, ITEM_SKIN):
        if _has_entry(source, name):
            raise ValueError(f'Map already contains {name}; refusing to replace existing Skin')
    tables = {}
    for name in (r'Units\UnitUI.slk', r'Units\ItemData.slk'):
        try:
            tables[name] = parse_slk(read_entry(source, name))
        except FileNotFoundError:
            tables[name] = []
    if not any(tables.values()):
        raise ValueError('Map has neither UnitUI.slk nor ItemData.slk')
    output = (output or source.with_name(source.stem + '_A_SKIN' + source.suffix)).resolve()
    if output == source or output.exists():
        raise FileExistsError(f'Refusing to overwrite existing file: {output}')
    report = (report or output.with_suffix('.report.txt')).resolve()
    if report == output:
        raise ValueError('Report path must differ from map path')
    if report.exists():
        raise FileExistsError(f'Report already exists: {report}')
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        skin_dir = client_dir or extract_client_skins(
            game or Path(r'C:\Program Files (x86)\Warcraft III'), work / 'client')
        entries = {}
        if tables[r'Units\UnitUI.slk']:
            entries[UNIT_SKIN] = build_skin(tables[r'Units\UnitUI.slk'],
                                            (skin_dir / 'unitskin.txt').read_bytes(), 'unitUIID', 'unit')
        if tables[r'Units\ItemData.slk']:
            entries[ITEM_SKIN] = build_skin(tables[r'Units\ItemData.slk'],
                                            (skin_dir / 'itemskin.txt').read_bytes(), 'itemID', 'item')
        entries = {name: data for name, data in entries.items() if data.count(b'skinType=')}
        if not entries:
            raise ValueError('No missing or overridden model mappings; no output created')
        source_records = archive_snapshot(source)
        staged = work / ('staged' + source.suffix)
        shutil.copyfile(source, staged)
        if header == PROTECTED_HEADER:
            with staged.open('r+b') as handle:
                handle.seek(offset + 4)
                handle.write(struct.pack('<I', 32))
        with _archive(staged, 0) as archive:
            add = _functions()[-1]
            for index, (name, content) in enumerate(entries.items()):
                payload = work / f'payload-{index}.bin'
                payload.write_bytes(content)
                if not add(archive, str(payload), name.encode('ascii'), 0x200, 0x02, 0):
                    raise OSError(c.get_last_error(), f'Cannot add {name}')
        for name, content in entries.items():
            if read_entry(staged, name) != content:
                raise ValueError(f'MPQ readback mismatch: {name}')
        output_records = archive_snapshot(staged)
        ordinary = lambda records: Counter({k: v for k, v in records.items() if k[0] not in METADATA})
        expected = ordinary(source_records)
        for name, content in entries.items():
            expected[(name.lower(), 0, len(content), sha(content))] += 1
        if ordinary(output_records) != expected:
            raise ValueError('Archive audit failed: unexpected gameplay payload change')
        changed_metadata = sum(source_records[k] for k in source_records
                               if k[0] in METADATA and output_records[k] != source_records[k])
        for key in output_records:
            if key[0] in METADATA and key not in source_records:
                if key[0] not in {x[0] for x in source_records if x[0] in METADATA}:
                    raise ValueError('Unexpected archive metadata entry')
        if staged.read_bytes()[:offset] != raw[:offset]:
            raise ValueError('Game header/prefix changed')
        if sha(source.read_bytes()) != before_hash:
            raise ValueError('Source changed during build')
        if output.exists() or report.exists():
            raise FileExistsError('Output or report appeared during build')
        staged_hash = sha(staged.read_bytes())
        published = _write_exclusive(output, staged)
    try:
        if sha(output.read_bytes()) != staged_hash:
            raise ValueError('Output copy verification failed')
    except BaseException:
        _remove_owned(output, published)
        raise
    result = {
        'status': 'SUCCESS_STRUCTURAL', 'source': str(source), 'source_sha256': before_hash,
        'output': str(output), 'output_sha256': sha(output.read_bytes()),
        'unit_sections': entries.get(UNIT_SKIN, b'').count(b'skinType=unit'),
        'item_sections': entries.get(ITEM_SKIN, b'').count(b'skinType=item'),
        'source_payloads': sum(source_records.values()),
        'unchanged_payloads': sum(source_records.values()) - changed_metadata,
        'metadata_rewritten': changed_metadata, 'read_errors': 0,
        'report': str(report),
    }
    text = ('Status: SUCCESS_STRUCTURAL\n'
            f'Source: {source}\nSource SHA-256: {before_hash}\n'
            f'Output: {output}\nOutput SHA-256: {result["output_sha256"]}\n'
            f'Added Skin sections: units={result["unit_sections"]}, items={result["item_sections"]}\n'
            f'Archive: {result["unchanged_payloads"]} unchanged source payloads; '
            f'{changed_metadata} metadata entries rewritten; 0 read errors.\n'
            'Archive structure verified.\n')
    try:
        _write_exclusive(report, text.encode('utf-8'))
    except BaseException:
        _remove_owned(output, published)
        raise
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path, help='Original .w3x/.w3m')
    parser.add_argument('--output', type=Path, help='New copy; default: *_A_SKIN.w3x')
    parser.add_argument('--game', type=Path, help='Warcraft III installation root')
    args = parser.parse_args()
    try:
        result = run(args.source, output=args.output, game=args.game)
    except Exception as error:
        print(f'FAILED: {type(error).__name__}: {error}', file=sys.stderr)
        return 1
    print(f'SUCCESS_STRUCTURAL: units={result["unit_sections"]}, '
          f'items={result["item_sections"]}')
    print('Map:', result['output'])
    print('Report:', result['report'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
