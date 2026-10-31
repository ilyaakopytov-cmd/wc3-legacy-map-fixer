import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auto_skin import _write_exclusive, _remove_owned


class ExclusivePublishTests(unittest.TestCase):
    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'staged.w3x'
            dest = Path(tmp) / 'target.w3x'
            source.write_bytes(b'new')
            dest.write_bytes(b'existing')
            with self.assertRaises(FileExistsError):
                _write_exclusive(dest, source)
            self.assertEqual(dest.read_bytes(), b'existing')

    def test_copy_does_not_rename_across_volumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'staged.w3x'
            dest = Path(tmp) / 'target.w3x'
            source.write_bytes(b'new')
            with patch('auto_skin.os.replace', side_effect=AssertionError('rename is unsafe')):
                identity = _write_exclusive(dest, source)
            self.assertEqual(dest.read_bytes(), b'new')
            self.assertTrue(_remove_owned(dest, identity))
            self.assertFalse(dest.exists())

    def test_partial_copy_does_not_leave_a_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'staged.w3x'
            dest = Path(tmp) / 'target.w3x'
            source.write_bytes(b'new')
            def fail_copy(inp, out, **kwargs):
                out.write(b'partial')
                raise OSError('copy interrupted')
            with patch('auto_skin.shutil.copyfileobj', side_effect=fail_copy):
                with self.assertRaisesRegex(OSError, 'copy interrupted'):
                    _write_exclusive(dest, source)
            self.assertFalse(dest.exists())

    def test_destination_is_invisible_while_copy_is_in_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'staged.w3x'
            dest = Path(tmp) / 'target.w3x'
            source.write_bytes(b'complete map')
            def inspect_copy(inp, out, **kwargs):
                self.assertFalse(dest.exists())
                out.write(inp.read())
            with patch('auto_skin.shutil.copyfileobj', side_effect=inspect_copy):
                _write_exclusive(dest, source)
            self.assertEqual(dest.read_bytes(), b'complete map')

    def test_competing_file_at_publish_time_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'staged.w3x'
            dest = Path(tmp) / 'target.w3x'
            source.write_bytes(b'ours')
            original_rename = os.rename
            def race(src, dst):
                dest.write_bytes(b'competitor')
                return original_rename(src, dst)
            with patch('auto_skin.os.rename', side_effect=race):
                with self.assertRaises(FileExistsError):
                    _write_exclusive(dest, source)
            self.assertEqual(dest.read_bytes(), b'competitor')

    def test_cleanup_does_not_delete_replaced_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'target.w3x'
            identity = _write_exclusive(dest, b'first')
            dest.unlink()
            dest.write_bytes(b'someone else')
            self.assertFalse(_remove_owned(dest, identity))
            self.assertEqual(dest.read_bytes(), b'someone else')


if __name__ == '__main__':
    unittest.main()
