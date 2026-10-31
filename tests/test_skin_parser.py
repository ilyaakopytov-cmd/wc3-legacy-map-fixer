import unittest
from tools.compat_patch import parse_slk


class SlkQuotedValueTests(unittest.TestCase):
    def test_semicolon_coordinate_markers_inside_quoted_model_are_data(self):
        raw = (b'ID;PWXL;N;E\r\nB;X2;Y2;D0\r\n'
               b'C;X1;Y1;K"unitUIID"\r\nC;X2;K"file"\r\n'
               b'C;X1;Y2;K"H01Z"\r\n'
               b'C;X2;K"model;X7;Y3;Kvalue"\r\nE\r\n')
        self.assertEqual(parse_slk(raw), [
            {'unitUIID': 'H01Z', 'file': 'model;X7;Y3;Kvalue'}])


if __name__ == '__main__':
    unittest.main()
