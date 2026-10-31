"""Generate compatibility Skin data from legacy Warcraft III SLK tables."""

import re


def parse_slk(data: bytes) -> list[dict[str, str]]:
    """Read inherited X/Y SYLK cells, including quoted semicolons and escaped quotes."""
    rows: dict[int, dict[int, str]] = {}
    x = y = 0
    for line in data.decode('utf-8-sig').splitlines():
        if not line.startswith('C;'):
            continue
        coordinates, marker, value = line.partition(';K')
        x_match = re.search(r'(?:^|;)X(\d+)(?:;|$)', coordinates)
        y_match = re.search(r'(?:^|;)Y(\d+)(?:;|$)', coordinates)
        if x_match:
            x = int(x_match[1])
        if y_match:
            y = int(y_match[1])
        if marker:
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1].replace('""', '"')
            rows.setdefault(y, {})[x] = value
    header = rows.pop(1)
    return [
        {name: cells.get(column, '') for column, name in header.items()}
        for _, cells in sorted(rows.items())
    ]


def build_skin(rows: list[dict[str, str]], client_data: bytes, id_field: str, kind: str) -> bytes:
    """Emit only map IDs absent from the client or with different Classic model art."""
    client: dict[str, list[dict[str, str]]] = {}
    current: dict[str, str] | None = None
    for line in client_data.decode('utf-8-sig').splitlines():
        if line.startswith('[') and line.endswith(']'):
            current = {}
            client.setdefault(line[1:-1], []).append(current)
        elif '=' in line and current is not None:
            key, value = line.split('=', 1)
            current[key] = value

    def canonical(value: str) -> str:
        return re.sub(r'\.(?:mdx|mdl)$', '', value.replace('/', '\\').lower())

    parts: list[str] = []
    for row in rows:
        id_ = row[id_field]
        if not re.fullmatch(r'[A-Za-z0-9]{4}', id_):
            raise ValueError(f'Invalid object ID: {id_!r}')
        model = row['file']
        if not model or '\r' in model or '\n' in model:
            raise ValueError(f'Invalid model for {id_}: {model!r}')
        if any(canonical(model) == canonical(skin.get('file:sd', skin.get('file', '')))
               for skin in client.get(id_, [])):
            continue
        entries = [f'[{id_}]', f'skinType={kind}', f'skinnableID={id_}', f'file={model}']
        optional = ('armor', 'unitSound') if kind == 'unit' else ('armor', 'scale', 'selSize', 'colorR', 'colorG', 'colorB')
        for field in optional:
            value = row.get(field, '')
            if value:
                if '\r' in value or '\n' in value:
                    raise ValueError(f'Invalid {field} for {id_}')
                entries.append(f'{field}={value}')
        parts.append('\r\n'.join(entries))
    return ('\r\n\r\n'.join(parts) + '\r\n').encode('utf-8')


def drop_slk_column(data: bytes, column_name: str) -> bytes:
    """Remove one SYLK column; keep all other K values and their row order."""
    x = y = 0
    doomed = None
    for line in data.splitlines():
        if not line.startswith(b'C;'):
            continue
        mx = re.search(rb'(?:^|;)X(\d+)(?:;|$)', line)
        my = re.search(rb'(?:^|;)Y(\d+)(?:;|$)', line)
        if mx:
            x = int(mx[1])
        if my:
            y = int(my[1])
        if y == 1 and line.partition(b';K')[2] == f'"{column_name}"'.encode():
            doomed = x
            break
    if doomed is None or doomed == 1:
        raise ValueError(f'Cannot remove SYLK column: {column_name}')

    x = 0
    parts = []
    for line in data.splitlines(keepends=True):
        if line.startswith(b'B;'):
            width = re.search(rb'(?:^|;)X(\d+)(?:;|$)', line.rstrip(b'\r\n'))
            if not width:
                raise ValueError('Missing SYLK bounds')
            line = line[:width.start(1)] + str(int(width[1]) - 1).encode() + line[width.end(1):]
        elif line.startswith(b'C;'):
            match = re.search(rb'(?:^|;)X(\d+)(?:;|$)', line.rstrip(b'\r\n'))
            if match:
                x = int(match[1])
            if x == doomed:
                continue
            adjusted = x - 1 if x > doomed else x
            # Explicit X on every retained cell makes inheritance independent of
            # removed cells. Original K literals, row coordinates and order remain.
            if match:
                line = line[:match.start(1)] + str(adjusted).encode() + line[match.end(1):]
            else:
                line = b'C;X' + str(adjusted).encode() + line[1:]
        parts.append(line)
    return b''.join(parts)
