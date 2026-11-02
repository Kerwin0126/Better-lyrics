# Author: Kerwin
"""Rounded native host-backdrop visual, clipped by the Windows compositor."""
import ctypes
import sys
from app_paths import RESOURCE_DIR

_library = None
_load_failed = False


def library():
    global _library, _load_failed
    if _library is None and not _load_failed and sys.platform == 'win32':
        try:
            _library = ctypes.CDLL(str(RESOURCE_DIR / 'RoundedBackdrop.dll'))
            _library.fl_blur_update.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 7
            _library.fl_blur_update.restype = ctypes.c_long
            _library.fl_blur_close.argtypes = []
            _library.fl_blur_close.restype = None
        except OSError:
            _load_failed = True
    return _library


def set_blur(hwnd, enabled, width=0, height=0, radius=0, x=0, y=0, topmost=True):
    native = library()
    if native is None:
        return False
    return native.fl_blur_update(hwnd, x, y, width, height, radius, int(topmost), int(enabled)) >= 0


def close_blur():
    if _library is not None:
        _library.fl_blur_close()
