# Warcraft III Legacy Map Fixer / Исправление старых карт Warcraft III

[Русский](#русский) · [English](#english)

## Русский

### Зачем это нужно

Некоторые старые пользовательские карты задают соответствия **ID объекта → путь к модели** в таблицах `Units/UnitUI.slk` и `Units/ItemData.slk`. В клиенте Warcraft III: Reforged (ветка **1.32**, выпущена в январе 2020 года) также используются файлы `Units/UnitSkin.txt` и `Units/ItemSkin.txt`. После обновления **2.0.0** (ноябрь 2024 года) пользователи сообщали о невидимых моделях, а для **3.0.0** (2026 год) сообщалось и об отдельных сбоях карт, использующих SLK. Это **не** означает, что Skin-файлы стали обязательны для всех карт с одной конкретной версии; причины несовместимости различаются.

**A-SKIN** — узкое средство для карт, у которых старые SLK содержат пути моделей, но отсутствуют соответствующие записи Skin. Оно извлекает Classic Skin-таблицы из установленной игры, добавляет недостающие/отличающиеся соответствия в **отдельную копию** карты и перечитывает её MPQ-архив. Исходные SLK и игровой скрипт не переписываются. Инструмент не заменяет сами модели и не устраняет все возможные проблемы карт, в частности отдельные ошибки чтения SLK в версии 3.0.0. Статус `SUCCESS_STRUCTURAL` означает успешную запись и проверку структуры архива.

Источники о версиях: [выпуск Reforged 28.01.2020](https://news.blizzard.com/en-us/article/23237899/warcraft-iii-reforged-releases-on-january-28-2020), [примечания к 2.0.0](https://news.blizzard.com/en-us/article/24167122/warcraft-iii-reforged-patch-notes-patch-2-0-0), [сообщения о невидимых моделях](https://us.forums.blizzard.com/en/warcraft3/t/invisible-units-in-classic-campaign/33675), [сообщение о SLK в 3.0.0](https://us.forums.blizzard.com/en/warcraft3/t/patch-300-crashes-custom-maps-that-use-slk-data/38840). Эти сообщения описывают контекст проблемы, но не доказывают, что A-SKIN исправляет каждый из перечисленных случаев.

### Что требуется

- Windows и установленный **Python 3.10+** с запуском через `py -3`.
- Установленный Warcraft III с папкой `Data`. Путь по умолчанию: `C:\Program Files (x86)\Warcraft III`; в меню можно указать другой.
- Исходная карта `.w3x` или `.w3m`, содержащая `Units/UnitUI.slk` и/или `Units/ItemData.slk`.
- Интернет при **первой конвертации**: скрипт скачивает `CASCConsole` из [релиза WoW-Tools/CASCExplorer v1.0.240](https://github.com/WoW-Tools/CASCExplorer/releases/tag/CASCExplorer-v1.0.240), проверяет SHA-256 ZIP и EXE и сохраняет утилиту локально. Последующие запуски используют её без повторной загрузки. Игровые Skin-таблицы извлекаются из *вашей установки* Warcraft III, в репозитории их нет.
- `tools/StormLib.dll` — x64 DLL из [официального релиза StormLib v9.40](https://github.com/ladislav-zezula/StormLib/releases/tag/v9.40), SHA-256 `93321f6f030be5d7d79eb4cbf433d6ef7e83ce20d47d8963717f207d54afbe16`, включена вместе с [разрешением MIT](tools/StormLib-LICENSE.txt). Сторонний CASCConsole **не включён** в репозиторий: он загружается непосредственно из релиза автора.

### Запуск

1. Скачайте репозиторий (кнопка **Code → Download ZIP**) и распакуйте его, **или** выполните `git clone`.
2. Запустите `run_A_SKIN.bat` в распакованной папке.
3. Выберите `1` — русский или `2` — английский. В меню: `1` — папка игры (Enter восстанавливает путь по умолчанию), `2` — конвертировать карту (введите полный путь к карте, допустимы кавычки), `3` — история, `0` — выход.
4. Новая карта появится в `corrected maps/`, отчёт — в `reports/`. Попытки, в том числе ошибочные, записываются в `history.jsonl` и показываются в меню. Повторный запуск не перезаписывает карту или отчёт: имена получают суффиксы `_2`, `_3` и т. д. Исходная карта остаётся на месте без изменений.

Для вызова без меню: `py -3 auto_skin.py --source "C:\путь\карта.w3x" --game "D:\Games\Warcraft III" --output "D:\путь\новая_карта.w3x"` (при прямом вызове отчёт создаётся рядом с указанным результатом).

Проверка тестов: `py -3 -m unittest discover -s tests -v`.

## English

### Why this tool exists

Some legacy custom maps keep **object ID → model path** mappings in `Units/UnitUI.slk` and `Units/ItemData.slk`. Warcraft III: Reforged (the **1.32** series, released in January 2020) also uses `Units/UnitSkin.txt` and `Units/ItemSkin.txt`. Users reported invisible models after the **2.0.0** update (November 2024), and separate SLK-related map failures were reported for **3.0.0** (2026). This does **not** mean every map started requiring Skin files in one particular version: compatibility problems have different causes.

**A-SKIN** addresses a narrow case: an old map has model paths in its SLK tables but lacks the corresponding Skin entries. The tool reads Classic Skin data from the locally installed game, adds missing or overridden mappings to a **separate map copy**, and checks the written MPQ archive. It does not rewrite the original SLK tables or gameplay script, replace model assets, or solve every possible SLK regression in 3.0.0. `SUCCESS_STRUCTURAL` means the archive was written and structurally verified.

Version references: [Reforged release, Jan 28, 2020](https://news.blizzard.com/en-us/article/23237899/warcraft-iii-reforged-releases-on-january-28-2020), [2.0.0 patch notes](https://news.blizzard.com/en-us/article/24167122/warcraft-iii-reforged-patch-notes-patch-2-0-0), [invisible-unit reports](https://us.forums.blizzard.com/en/warcraft3/t/invisible-units-in-classic-campaign/33675), [3.0.0 SLK regression report](https://us.forums.blizzard.com/en/warcraft3/t/patch-300-crashes-custom-maps-that-use-slk-data/38840). The reports provide context; they do not establish that A-SKIN fixes every reported case.

### Requirements

- Windows and **Python 3.10+** with the `py -3` launcher.
- A Warcraft III installation containing `Data`. Default path: `C:\Program Files (x86)\Warcraft III`; choose another directory in the menu if necessary.
- A `.w3x` or `.w3m` source map with `Units/UnitUI.slk` and/or `Units/ItemData.slk`.
- Internet access on the **first conversion**: the tool downloads `CASCConsole` directly from the [WoW-Tools/CASCExplorer v1.0.240 release](https://github.com/WoW-Tools/CASCExplorer/releases/tag/CASCExplorer-v1.0.240), checks the ZIP and EXE SHA-256 digests, and keeps it locally for future runs. The game's Skin tables come from *your installed client*; they are not in this repository.
- `tools/StormLib.dll` is the x64 DLL from the [official StormLib v9.40 release](https://github.com/ladislav-zezula/StormLib/releases/tag/v9.40), SHA-256 `93321f6f030be5d7d79eb4cbf433d6ef7e83ce20d47d8963717f207d54afbe16`, included under its [MIT notice](tools/StormLib-LICENSE.txt). The third-party CASCConsole binary is **not included** in the repository.

### How to use

1. Download and extract the repository via **Code → Download ZIP**, or clone it with Git.
2. Run `run_A_SKIN.bat` in the extracted directory.
3. Select `1` for Russian or `2` for English. In the menu: `1` — game directory (Enter restores the default), `2` — convert a map (paste its full path; quotes are accepted), `3` — history, `0` — exit.
4. Find the map copy in `corrected maps/` and its report in `reports/`. All conversion attempts, including failures, are recorded in `history.jsonl` and displayed in the menu. Repeated conversions use `_2`, `_3`, etc., instead of overwriting previous outputs. The source map remains unchanged.

For non-interactive use: `py -3 auto_skin.py --source "C:\path\map.w3x" --game "D:\Games\Warcraft III" --output "D:\path\new_map.w3x"` (direct CLI use places the report next to the specified output).

Run tests with `py -3 -m unittest discover -s tests -v`.
