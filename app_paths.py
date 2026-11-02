# Author: Kerwin
"""Writable app files beside the EXE; bundled assets inside its runtime folder."""
from pathlib import Path
import sys
import os

RESOURCE_DIR = Path(__file__).resolve().parent
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else RESOURCE_DIR
INSTALLED = (APP_DIR/'installed.flag').is_file()
DATA_DIR = Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))/'BetterLyrics' if INSTALLED else APP_DIR
if INSTALLED:DATA_DIR.mkdir(parents=True,exist_ok=True)
APP_ICON = RESOURCE_DIR / 'assets' / 'floating-lyrics.ico'
