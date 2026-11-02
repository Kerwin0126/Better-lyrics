# Author: Kerwin
"""Exercise the actual Qt renderer: alpha, colors, opacity, wrapping, persistence."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QFontDatabase
from pathlib import Path
from PySide6.QtCore import Qt
from desktop_lyrics import Appearance, LyricCanvas, wrapped_lines

app = QApplication([])
for name in ('msyh.ttc','msyhbd.ttc'):
    font_file=Path('C:/Windows/Fonts') / name
    if font_file.is_file(): QFontDatabase.addApplicationFont(str(font_file))
style = Appearance(color='#8FF0CE', opacity=100, outline=False, next_line=False)
canvas = LyricCanvas(style)
canvas.resize(900, 160)
canvas.set_content('透明歌词 · Keep Real')
assert canvas.windowFlags() & Qt.WindowType.FramelessWindowHint
assert canvas.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
style.locked = True
canvas.apply_flags()
assert canvas.windowFlags() & Qt.WindowType.WindowTransparentForInput
style.locked = False
canvas.apply_flags()
assert not canvas.windowFlags() & Qt.WindowType.WindowTransparentForInput

def render():
    result = QImage(canvas.size(), QImage.Format.Format_ARGB32)
    result.fill(Qt.GlobalColor.transparent)
    canvas.render(result)
    return result

image = render()
assert all(image.pixelColor(x, y).alpha() == 0 for x, y in [(0,0), (899,0), (0,159), (899,159), (450,5)])
pixels = [image.pixelColor(x, y) for y in range(image.height()) for x in range(image.width())]
solid = [color for color in pixels if color.alpha() == 255]
assert len(solid) > 50
assert all(color.name().upper() == '#8FF0CE' for color in solid)
transparent_fraction = sum(color.alpha() == 0 for color in pixels) / len(pixels)
print('transparent fraction:', round(transparent_fraction, 3))
assert transparent_fraction > .65
style.color = '#FFBE91'
style.opacity = 50
image = render()
colors = [image.pixelColor(x, y) for y in range(image.height()) for x in range(image.width())]
maximum = max(color.alpha() for color in colors)
assert 126 <= maximum <= 129, maximum
assert any(color.alpha() >= 126 and abs(color.red() - 255) <= 2 and
           abs(color.green() - 190) <= 2 and abs(color.blue() - 145) <= 2 for color in colors)
assert len(wrapped_lines('这是一句很长很长的歌词用来检查换行不会截断任何文字', canvas.text_font(), 150)) > 1
print('PASS: transparent corners/background, solid custom color, live color/opacity changes, full-text wrapping')
