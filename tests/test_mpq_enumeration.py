import ctypes as c
import unittest

from auto_skin import _advance_find


class MpqEnumerationTests(unittest.TestCase):
    def test_end_of_archive_is_not_an_error(self):
        def end(*args):
            c.set_last_error(18)  # ERROR_NO_MORE_FILES
            return False
        self.assertFalse(_advance_find(end, object(), c.c_uint32()))

    def test_read_error_does_not_look_like_end_of_archive(self):
        def fail(*args):
            c.set_last_error(5)  # ERROR_ACCESS_DENIED
            return False
        with self.assertRaises(OSError):
            _advance_find(fail, object(), c.c_uint32())


if __name__ == '__main__':
    unittest.main()
