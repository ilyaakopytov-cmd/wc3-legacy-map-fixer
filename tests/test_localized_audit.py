from collections import Counter
import ctypes as c
from pathlib import Path
import tempfile
import unittest

from auto_skin import archive_snapshot, METADATA
from tools.mpq import _archive, _functions, read_entry


class LocalizedArchiveAuditTests(unittest.TestCase):
    def test_changed_nondefault_locale_payload_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'localized.w3x'
            dll = c.WinDLL(str(Path(__file__).resolve().parents[1] / 'tools/StormLib.dll'), use_last_error=True)
            create = dll.SFileCreateArchive
            create.argtypes = [c.c_wchar_p, c.c_uint32, c.c_uint32, c.POINTER(c.c_void_p)]
            create.restype = c.c_bool
            set_locale = dll.SFileSetLocale
            set_locale.argtypes = [c.c_uint32]
            set_locale.restype = c.c_uint32
            close = _functions()[1]
            add = _functions()[-1]
            handle = c.c_void_p()
            self.assertTrue(create(str(path), 0, 16, c.byref(handle)))
            try:
                for locale, text in [(0, b'neutral'), (0x409, b'english')]:
                    source = Path(tmp) / f'{locale}.bin'
                    source.write_bytes(text)
                    set_locale(locale)
                    self.assertTrue(add(handle, str(source), b'war3map.w3i', 0x200, 2, 0))
            finally:
                close(handle)
            set_locale(0)
            before = archive_snapshot(path)
            with _archive(path, 0) as archive:
                changed = Path(tmp) / 'changed.bin'
                changed.write_bytes(b'changed english')
                set_locale(0x409)
                self.assertTrue(add(archive, str(changed), b'war3map.w3i', 0x80000200, 2, 0))
            self.assertEqual(read_entry(path, 'war3map.w3i'), b'changed english')
            set_locale(0)
            after = archive_snapshot(path)
            ordinary = lambda records: Counter({k: v for k, v in records.items() if k[0] not in METADATA})
            self.assertNotEqual(ordinary(before), ordinary(after))


if __name__ == '__main__':
    unittest.main()
