# Author: Kerwin
"""Shared lyric decoding and matching without a GUI toolkit dependency."""
from __future__ import annotations
from bisect import bisect_right
from dataclasses import dataclass
import os
from pathlib import Path
import re
import unicodedata
import zlib

KRC_KEY = bytes([64, 71, 97, 119, 94, 50, 116, 71, 81, 54, 49, 45, 206, 210, 110, 105])
MAX_BYTES = 8 * 1024 * 1024


@dataclass
class LyricLine:
    start_ms: int
    duration_ms: int | None
    text: str
    words: list[tuple[int, int, str]]


def decode_file(path: Path) -> str:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('文件过大，当前原型仅支持 8 MB 以内的歌词。')
    data = path.read_bytes()
    if path.suffix.lower() == '.krc':
        if data[:4] != b'krc1':
            raise ValueError('不是支持的 krc1 文件。')
        packed = bytes(v ^ KRC_KEY[i % len(KRC_KEY)] for i, v in enumerate(data[4:]))
        decoder = zlib.decompressobj()
        data = decoder.decompress(packed, MAX_BYTES + 1)
        if len(data) > MAX_BYTES or not decoder.eof:
            raise ValueError('KRC 解压数据过大或文件不完整。')
    for encoding in ('utf-8-sig', 'utf-16', 'gb18030'):
        try:
            return data.decode(encoding)
        except UnicodeError:
            pass
    raise ValueError('无法识别歌词文本编码。')


def parse_lyrics(text: str, kind: str) -> tuple[dict[str, str], list[LyricLine]]:
    meta: dict[str, str] = {}
    lines: list[LyricLine] = []
    for raw in text.splitlines():
        m = re.fullmatch(r'\[([A-Za-z]+):(.*)\]', raw.strip())
        if m:
            meta[m[1].lower()] = m[2]
            continue
        if kind.lower() == '.krc':
            m = re.match(r'^\[(\d+),(\d+)\](.*)$', raw)
            if not m:
                continue
            words = [(int(w[1]), int(w[2]), w[3]) for w in
                     re.finditer(r'<(\d+),(\d+),\d+>([^<]*)', m[3])]
            clean = re.sub(r'<\d+,\d+,\d+>', '', m[3])
            lines.append(LyricLine(int(m[1]), int(m[2]), clean, words))
        else:
            stamps = re.findall(r'\[(\d+):(\d+(?:\.\d+)?)\]', raw)
            clean = re.sub(r'\[\d+:\d+(?:\.\d+)?\]', '', raw)
            for minutes, seconds in stamps:
                lines.append(LyricLine(round((int(minutes) * 60 + float(seconds)) * 1000), None, clean, []))
    lines.sort(key=lambda line: line.start_ms)
    if not lines:
        raise ValueError('文件中未找到支持的带时间戳歌词。')
    return meta, lines


def discover_folder() -> Path:
    config_path = Path(os.environ.get('APPDATA', '')) / 'KuGou8' / 'KuGou.ini'
    if config_path.is_file():
        data = config_path.read_bytes()
        for enc in ('utf-8-sig', 'utf-16', 'gb18030'):
            try:
                text = data.decode(enc)
            except UnicodeError:
                continue
            # Read only the lyric-directory setting; do not modify the player config.
            m = re.search(r'^LyricPath\s*=\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m and Path(m[1].strip().strip('"')).is_dir():
                return Path(m[1].strip().strip('"'))
    for folder in (Path.home() / 'Music' / 'KuGou' / 'Lyric',):
        if folder.is_dir():
            return folder
    return Path.home() / 'Music'


def scan(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise ValueError('目录不存在，请选择酷狗的歌词目录。')
    return sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ('.krc', '.lrc')),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def short_name(path: Path) -> str:
    return re.sub(r'-[0-9a-fA-F]{32}-\d+-[0-9a-fA-F]+$', '', path.stem)


def stamp(ms: int) -> str:
    return f'{ms // 60000:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}'


def normalize_identity(value: str) -> str:
    value = unicodedata.normalize('NFKC', value).casefold()
    return re.sub(r'[\s、/,，&]+', '', value)


def match_file(files: list[Path], identity: str) -> Path | None:
    key = normalize_identity(identity)
    # Exact song/version and artists, never substitute an arbitrary recent cache.
    return next((p for p in files if normalize_identity(short_name(p)) == key), None)


def active_line(lines: list[LyricLine], position_ms: int) -> int:
    index = bisect_right([line.start_ms for line in lines], position_ms) - 1
    if index >= 0:
        line = lines[index]
        if line.duration_ms is not None and position_ms >= line.start_ms + line.duration_ms:
            return -1
    return index


