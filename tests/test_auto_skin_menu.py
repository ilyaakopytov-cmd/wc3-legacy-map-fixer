import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from auto_skin_menu import run_menu


class MenuTests(unittest.TestCase):
    def test_bat_opens_language_menu_then_english_main_menu(self):
        bat = Path(__file__).resolve().parents[1] / 'run_A_SKIN.bat'
        result = subprocess.run([str(bat)], shell=True, input='2\n0\n',
                                capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn('Choose language', result.stdout)
        self.assertIn('Correction history', result.stdout)
        self.assertIn('Goodbye.', result.stdout)

    def test_russian_menu_selects_game_converts_to_corrected_maps_and_lists_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            game = root / 'игра'
            (game / 'Data').mkdir(parents=True)
            source = root / 'карта.w3x'
            source.write_bytes(b'original')
            seen = []
            def convert(path, *, output, report, game):
                seen.append((path, output, report, game))
                output.write_bytes(b'corrected')
                report.parent.mkdir(parents=True, exist_ok=True)
                report.write_text('SUCCESS_STRUCTURAL', encoding='utf-8')
                return {'status': 'SUCCESS_STRUCTURAL', 'output': str(output),
                        'report': str(report), 'unit_sections': 12, 'item_sections': 3,
                        'output_sha256': 'example'}
            inputs = iter(['1', '1', str(game), '2', f'"{source}"', '3', '0'])
            lines = []
            run_menu(root=root, default_game=root / 'default',
                     input_fn=lambda prompt: next(inputs), print_fn=lines.append, converter=convert)
            target = root / 'corrected maps/карта_A_SKIN.w3x'
            expected_report = root / 'reports/карта_A_SKIN.report.txt'
            self.assertEqual(seen, [(source, target, expected_report, game)])
            self.assertTrue(target.is_file())
            self.assertTrue(expected_report.is_file())
            self.assertEqual(list((root / 'corrected maps').iterdir()), [target])
            entries = [json.loads(x) for x in (root / 'history.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['status'], 'SUCCESS_STRUCTURAL')
            self.assertEqual(entries[0]['source'], str(source))
            self.assertEqual(entries[0]['report'], str(expected_report))
            self.assertNotIn('не тестировалась', '\n'.join(lines).lower())
            self.assertIn('1.', '\n'.join(lines))
            self.assertIn('История', '\n'.join(lines))
            self.assertIn('12', '\n'.join(lines))

    def test_english_failed_attempt_persists_and_is_numbered_next_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'bad.w3x'
            source.write_bytes(b'bad')
            def fail(*args, **kwargs):
                raise ValueError('unsupported MPQ')
            lines = []
            inputs = iter(['2', '2', str(source), '0'])
            run_menu(root=root, input_fn=lambda prompt: next(inputs), print_fn=lines.append, converter=fail)
            self.assertIn('FAILED', '\n'.join(lines))
            self.assertFalse((root / 'corrected maps/bad_A_SKIN.w3x').exists())
            lines2 = []
            inputs2 = iter(['2', '3', '0'])
            run_menu(root=root, input_fn=lambda prompt: next(inputs2), print_fn=lines2.append, converter=fail)
            self.assertIn('1.', '\n'.join(lines2))
            self.assertIn('unsupported MPQ', '\n'.join(lines2))
            entries = [json.loads(x) for x in (root / 'history.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['status'], 'FAILED')

    def test_existing_output_is_not_overwritten_and_new_name_is_numbered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'map.w3x'
            source.write_bytes(b'source')
            previous = root / 'corrected maps/map_A_SKIN.w3x'
            previous.parent.mkdir()
            previous.write_bytes(b'old result')
            old_report = root / 'reports/map_A_SKIN_2.report.txt'
            old_report.parent.mkdir()
            old_report.write_bytes(b'old report')
            def convert(path, *, output, report, game):
                output.write_bytes(b'new result')
                return {'status': 'SUCCESS_STRUCTURAL', 'output': str(output),
                        'report': str(report),
                        'unit_sections': 1, 'item_sections': 0, 'output_sha256': 'example'}
            inputs = iter(['2', '2', str(source), '0'])
            run_menu(root=root, input_fn=lambda prompt: next(inputs),
                     print_fn=lambda line: None, converter=convert)
            self.assertEqual(previous.read_bytes(), b'old result')
            self.assertEqual(old_report.read_bytes(), b'old report')
            self.assertEqual((root / 'corrected maps/map_A_SKIN_3.w3x').read_bytes(), b'new result')


if __name__ == '__main__':
    unittest.main()
