import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from setup_casc import ensure_casc, ZIP_SHA256, EXE_SHA256


def sample_zip(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buffer.getvalue()


class SetupTests(unittest.TestCase):
    def test_pinned_digests_are_sha256(self):
        for value in (ZIP_SHA256, EXE_SHA256):
            self.assertEqual(len(value), 64)
            self.assertTrue(all(c in '0123456789abcdef' for c in value))

    def test_downloads_verified_archive_once(self):
        data = sample_zip({'CASCConsole.exe': b'example executable',
                           'CascLib.dll': b'example dependency'})
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'CASCConsole'
            with patch('setup_casc.ZIP_SHA256', hashlib.sha256(data).hexdigest()), \
                 patch('setup_casc.EXE_SHA256', hashlib.sha256(b'example executable').hexdigest()), \
                 patch('setup_casc.download', return_value=data) as download:
                self.assertEqual(ensure_casc(target), target / 'CASCConsole.exe')
                self.assertEqual(ensure_casc(target), target / 'CASCConsole.exe')
                download.assert_called_once()
                self.assertEqual((target / 'CascLib.dll').read_bytes(), b'example dependency')

    def test_rejects_modified_release_and_leaves_no_partial_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'CASCConsole'
            with patch('setup_casc.download', return_value=b'bad'):
                with self.assertRaisesRegex(ValueError, 'SHA-256'):
                    ensure_casc(target)
            self.assertFalse(target.exists())

    def test_rejects_archive_path_traversal(self):
        data = sample_zip({'CASCConsole.exe': b'example executable',
                           '../escaped.txt': b'bad'})
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'CASCConsole'
            with patch('setup_casc.ZIP_SHA256', hashlib.sha256(data).hexdigest()), \
                 patch('setup_casc.EXE_SHA256', hashlib.sha256(b'example executable').hexdigest()), \
                 patch('setup_casc.download', return_value=data):
                with self.assertRaisesRegex(ValueError, 'Unsafe'):
                    ensure_casc(target)
            self.assertFalse(target.exists())
            self.assertFalse((Path(tmp) / 'escaped.txt').exists())


if __name__ == '__main__':
    unittest.main()
