# Author: Kerwin
# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

base = Path(SPECPATH)
analysis = Analysis([str(base / 'desktop_lyrics.py')], pathex=[str(base)],
    binaries=[(str(base / 'PlaybackReader.exe'), '.'), (str(base / 'RoundedBackdrop.dll'), '.'),
              (str(base / 'MediaReader.exe'), '.'), (str(base / 'QrcDecode.dll'), '.')],
    datas=[(str(base / 'assets' / 'floating-lyrics.ico'), 'assets'),
           (str(base / 'assets' / 'floating-lyrics.png'), 'assets'),
           (str(base / 'LICENSE'), '.'), (str(base / 'README.md'), '.'),
           (str(base / 'THIRD_PARTY_NOTICES.md'), '.'),
           (str(base / 'third_party'), 'third_party'),
           (str(base / 'docs'), 'docs')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter'], noarchive=False)
# Qt 6.12 uses Windows' unversioned ICU API. Python 3.14's Tcl ships an
# identically named ICU with versioned exports, which must not shadow it.
analysis.binaries = [entry for entry in analysis.binaries
    if Path(entry[0]).name.casefold() != 'icuuc.dll'
    and not Path(entry[0]).name.casefold().startswith('icudt')]
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name='浮词',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False,
    icon=str(base / 'assets' / 'floating-lyrics.ico'),
    version=str(base / 'version_info.txt'))
collection = COLLECT(exe, analysis.binaries, analysis.datas,
    strip=False, upx=False, name='浮词')
