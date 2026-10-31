"""Interactive bilingual Windows menu for the A-SKIN archive migration."""
from datetime import datetime
import json
from pathlib import Path

from auto_skin import run

ROOT = Path(__file__).resolve().parent
DEFAULT_GAME = Path(r'C:\Program Files (x86)\Warcraft III')

TEXT = {
    'ru': {
        'language': 'Выберите язык / Choose language: 1 — Русский, 2 — English: ',
        'invalid_language': 'Введите 1 или 2 / Enter 1 or 2.',
        'heading': '\n=== Исправление карт Warcraft III (A-SKIN) ===',
        'current_game': 'Папка игры',
        'option1': '1. Указать папку игры (Enter — вернуть путь по умолчанию)',
        'option2': '2. Конвертировать карту',
        'option3': '3. История исправлений',
        'option0': '0. Выход',
        'choose': 'Выберите пункт: ',
        'game_prompt': 'Путь к папке Warcraft III (Enter — путь по умолчанию): ',
        'game_invalid': 'Папка Data не найдена. Путь не изменён.',
        'game_set': 'Папка игры установлена',
        'map_prompt': 'Введите путь к карте .w3x/.w3m и нажмите Enter (пусто — назад): ',
        'cancel': 'Отменено.',
        'working': 'Создаю копию и проверяю архив...',
        'success': 'УСПЕХ: архив проверен.',
        'failure': 'ОШИБКА: проверенная карта не создана.',
        'map': 'Карта',
        'report': 'Отчёт',
        'sections': 'Добавлено секций: юниты={units}, предметы={items}',
        'history': '\n=== История исправлений ===',
        'empty': 'История пуста.',
        'history_error': 'Не удалось прочитать историю',
        'history_write_error': 'ВНИМАНИЕ: не удалось сохранить историю',
        'exit': 'Выход.',
        'invalid_option': 'Нет такого пункта.',
        'hist_success': 'УСПЕХ (только архив)',
        'hist_failure': 'ОШИБКА',
    },
    'en': {
        'language': 'Choose language / Выберите язык: 1 — Русский, 2 — English: ',
        'invalid_language': 'Enter 1 or 2 / Введите 1 или 2.',
        'heading': '\n=== Warcraft III map correction (A-SKIN) ===',
        'current_game': 'Game directory',
        'option1': '1. Set game directory (Enter — restore default)',
        'option2': '2. Convert map',
        'option3': '3. Correction history',
        'option0': '0. Exit',
        'choose': 'Choose an option: ',
        'game_prompt': 'Warcraft III directory (Enter — use default): ',
        'game_invalid': 'Data directory not found. Path unchanged.',
        'game_set': 'Game directory set to',
        'map_prompt': 'Enter .w3x/.w3m map path and press Enter (empty — back): ',
        'cancel': 'Cancelled.',
        'working': 'Creating a copy and checking the archive...',
        'success': 'SUCCESS: archive verified.',
        'failure': 'FAILED: no verified map was created.',
        'map': 'Map',
        'report': 'Report',
        'sections': 'Added sections: units={units}, items={items}',
        'history': '\n=== Correction history ===',
        'empty': 'History is empty.',
        'history_error': 'Cannot read history',
        'history_write_error': 'WARNING: cannot save history',
        'exit': 'Goodbye.',
        'invalid_option': 'Unknown option.',
        'hist_success': 'SUCCESS (archive only)',
        'hist_failure': 'FAILED',
    },
}


def unquote(value: str) -> str:
    value = value.strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value


def free_output(source: Path, directory: Path, reports: Path) -> tuple[Path, Path]:
    """Choose matching unused map/report names without replacing old results."""
    base = source.stem + '_A_SKIN'
    counter = 1
    while True:
        suffix = '' if counter == 1 else f'_{counter}'
        candidate = directory / (base + suffix + source.suffix)
        report = reports / (candidate.stem + '.report.txt')
        if not candidate.exists() and not report.exists() and not candidate.with_suffix('.report.txt').exists():
            return candidate, report
        counter += 1


def history_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def run_menu(*, root: Path = ROOT, default_game: Path = DEFAULT_GAME,
             input_fn=input, print_fn=print, converter=run) -> None:
    root = Path(root).resolve()
    def ask(prompt: str) -> str:
        return input_fn(prompt)
    try:
        while True:
            choice = ask(TEXT['ru']['language']).strip().lower()
            if choice in ('1', 'ru'):
                lang = 'ru'
                break
            if choice in ('2', 'en'):
                lang = 'en'
                break
            print_fn(TEXT['ru']['invalid_language'])
        t = TEXT[lang]
        game = Path(default_game)
        history_path = root / 'history.jsonl'
        corrected = root / 'corrected maps'
        reports = root / 'reports'
        while True:
            print_fn(t['heading'])
            print_fn(f'{t["current_game"]}: {game}')
            for key in ('option1', 'option2', 'option3', 'option0'):
                print_fn(t[key])
            choice = ask(t['choose']).strip()
            if choice == '0':
                print_fn(t['exit'])
                return
            if choice == '1':
                value = unquote(ask(t['game_prompt']))
                if not value:
                    game = Path(default_game)
                    print_fn(f'{t["game_set"]}: {game}')
                else:
                    candidate = Path(value).expanduser().resolve()
                    if not (candidate / 'Data').is_dir():
                        print_fn(t['game_invalid'])
                    else:
                        game = candidate
                        print_fn(f'{t["game_set"]}: {game}')
                continue
            if choice == '2':
                value = unquote(ask(t['map_prompt']))
                if not value:
                    print_fn(t['cancel'])
                    continue
                source = Path(value).expanduser().resolve()
                entry = {'timestamp': datetime.now().astimezone().isoformat(timespec='seconds'),
                         'source': str(source), 'game': str(game)}
                try:
                    output, report = free_output(source, corrected, reports)
                    corrected.mkdir(parents=True, exist_ok=True)
                    print_fn(t['working'])
                    result = converter(source, output=output, report=report, game=game)
                    entry.update(status=result['status'], output=result['output'],
                                 report=result['report'], unit_sections=result['unit_sections'],
                                 item_sections=result['item_sections'], output_sha256=result['output_sha256'])
                    print_fn(t['success'])
                    print_fn(t['sections'].format(units=entry['unit_sections'], items=entry['item_sections']))
                    print_fn(f'{t["map"]}: {entry["output"]}')
                    print_fn(f'{t["report"]}: {entry["report"]}')
                except Exception as error:
                    entry.update(status='FAILED', error=f'{type(error).__name__}: {error}')
                    print_fn(f'{t["failure"]} {entry["error"]}')
                try:
                    with history_path.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(entry, ensure_ascii=False) + '\n')
                except OSError as error:
                    print_fn(f'{t["history_write_error"]}: {error}')
                continue
            if choice == '3':
                print_fn(t['history'])
                try:
                    records = history_lines(history_path)
                except (OSError, ValueError) as error:
                    print_fn(f'{t["history_error"]}: {error}')
                    continue
                if not records:
                    print_fn(t['empty'])
                for index, entry in enumerate(records, 1):
                    status = t['hist_success'] if entry['status'] == 'SUCCESS_STRUCTURAL' else t['hist_failure']
                    print_fn(f'{index}. {entry["timestamp"]} | {status} | {entry["source"]}')
                    if entry.get('output'):
                        print_fn(f'   {t["map"]}: {entry["output"]} | '
                                 + t['sections'].format(units=entry.get('unit_sections', 0),
                                                        items=entry.get('item_sections', 0)))
                    if entry.get('error'):
                        print_fn(f'   {entry["error"]}')
                continue
            print_fn(t['invalid_option'])
    except (EOFError, StopIteration, KeyboardInterrupt):
        print_fn('\n' + TEXT.get(locals().get('lang', 'en'), TEXT['en'])['exit'])


if __name__ == '__main__':
    run_menu()
