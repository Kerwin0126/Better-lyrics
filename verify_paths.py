# Author: Kerwin
"""Check cache discovery with relocated, quoted Chinese paths and config encodings."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from lyric_data import discover_folder

with TemporaryDirectory(prefix='floating-lyrics-paths-') as temporary:
    root = Path(temporary)
    profile, home = root / 'profile', root / 'home'
    config = profile / 'KuGou8' / 'KuGou.ini'
    config.parent.mkdir(parents=True)
    relocated = root / '另一位置' / '歌词 缓存'
    relocated.mkdir(parents=True)
    with patch.dict(os.environ, {'APPDATA': str(profile)}), patch.object(Path, 'home', return_value=home):
        for encoding in ('utf-8-sig', 'utf-16', 'gb18030'):
            config.write_text('[Lyric]\nLyricPath="' + str(relocated) + '"\n', encoding=encoding)
            assert discover_folder() == relocated, encoding
        config.write_text('LyricPath=' + str(root / 'missing'), encoding='utf-8')
        assert discover_folder() == home / 'Music'
        user_cache = home / 'Music' / 'KuGou' / 'Lyric'
        user_cache.mkdir(parents=True)
        assert discover_folder() == user_cache
print('PASS: relocated Chinese/spaced/quoted cache paths; UTF-8, UTF-16 and GB18030 config; per-user fallback without a fixed drive')
