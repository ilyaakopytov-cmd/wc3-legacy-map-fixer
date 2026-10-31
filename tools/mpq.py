"""Small StormLib reader/writer for Warcraft III MPQ archives."""
from contextlib import contextmanager
import ctypes as c
from pathlib import Path

DLL = Path(__file__).with_name('StormLib.dll')



def _functions():
    lib = c.WinDLL(str(DLL), use_last_error=True)
    def bind(name, args, result=c.c_bool):
        fn = getattr(lib, name)
        fn.argtypes = args
        fn.restype = result
        return fn
    return (
        bind('SFileOpenArchive', [c.c_wchar_p, c.c_uint32, c.c_uint32, c.POINTER(c.c_void_p)]),
        bind('SFileCloseArchive', [c.c_void_p]),
        bind('SFileOpenFileEx', [c.c_void_p, c.c_char_p, c.c_uint32, c.POINTER(c.c_void_p)]),
        bind('SFileCloseFile', [c.c_void_p]),
        bind('SFileGetFileSize', [c.c_void_p, c.c_void_p], c.c_uint32),
        bind('SFileReadFile', [c.c_void_p, c.c_void_p, c.c_uint32, c.POINTER(c.c_uint32), c.c_void_p]),
        bind('SFileAddFileEx', [c.c_void_p, c.c_wchar_p, c.c_char_p, c.c_uint32, c.c_uint32, c.c_uint32]),
    )


@contextmanager
def _archive(path, mode=0x100):
    open_archive, close_archive, *_ = _functions()
    handle = c.c_void_p()
    if not open_archive(str(path), 0, mode, c.byref(handle)):
        raise OSError(c.get_last_error(), f'Cannot open MPQ: {path}')
    try:
        yield handle
    finally:
        if not close_archive(handle):
            raise OSError(c.get_last_error(), f'Cannot close MPQ: {path}')


def read_entry(path: Path, name: str) -> bytes:
    _, _, open_file, close_file, size_file, read_file, _ = _functions()
    with _archive(path) as archive:
        handle = c.c_void_p()
        if not open_file(archive, name.encode('ascii'), 0, c.byref(handle)):
            raise FileNotFoundError(c.get_last_error(), name)
        try:
            size = size_file(handle, None)
            if size == 0xFFFFFFFF or size > 32_000_000:
                raise ValueError(f'Unexpected MPQ size: {name} ({size})')
            output = c.create_string_buffer(size)
            got = c.c_uint32()
            if not read_file(handle, output, size, c.byref(got), None) or got.value != size:
                raise OSError(c.get_last_error(), f'Cannot read {name}')
            return output.raw[:size]
        finally:
            close_file(handle)
