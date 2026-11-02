# Author: Kerwin
"""Render regressions: adjustable entrance, timed per-character wave and panel alpha."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QImage
from PySide6.QtCore import Qt
from desktop_lyrics import Appearance
from lyric_renderer import LyricCanvas, entry_zoom, wave_offset, singing_span, glyph_bitmap
from lyrics_viewer import LyricLine

app = QApplication([])
for name in ('msyh.ttc', 'msyhbd.ttc'):
    QFontDatabase.addApplicationFont(str(Path('C:/Windows/Fonts') / name))
assert entry_zoom(0, 100) < entry_zoom(0, 30) < entry_zoom(0, 0) == 1
assert entry_zoom(1, 100) == entry_zoom(1, 0) == 1
for phase in (0, 1):
    assert abs(wave_offset(phase, 0, 100, 100)) < 1e-10
assert abs(wave_offset(.25, 0, 100, 100)) > abs(wave_offset(.25, 0, 30, 100)) > 0
assert wave_offset(.25, 0, 100, 100) != wave_offset(.25, 1, 100, 100)
assert wave_offset(.25, 0, 100, 100) != wave_offset(.25, 0, 100, 200)
line = LyricLine(0, 4000, '晚风经过窗台', [(0, 1000, '晚风'), (1400, 2200, '经过窗台')])
assert singing_span(line, 250) == (0, 2, .25)
assert singing_span(line, 1200) is None
style = Appearance(mode='duet', size=40, next_line=False, word_glow=False, motion='none')
canvas = LyricCanvas(style)
canvas.resize(900, 220)
canvas.set_sequence([line], 0, 250, snap=True)

def render():
    image = QImage(canvas.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    canvas.render(image)
    return image

flat = render()
style.word_wave = True
style.wave_strength = 100
wave = render()
assert wave != flat, 'wave enabled but actual text pixels did not move'
assert wave == render(), 'paused position must freeze the wave'
style.wave_strength = 0
assert render() == flat, 'zero amplitude must render the original text'
style.wave_strength = 100
canvas.set_sequence([line], 0, 1200, snap=True)
gap = render()
style.word_wave = False
assert render() == gap, 'KRC token gap must return to the flat baseline'
assert render().pixelColor(450, 5).alpha() == 0
style.background_opacity = 40
style.background_radius = 60
style.opacity = 20
panel = render()
assert 100 <= panel.pixelColor(450, 5).alpha() <= 104, 'panel alpha must be independent of text opacity'
assert panel.pixelColor(0, 0).alpha() == 0, 'panel corners must stay transparent'
style.background_opacity = 0
assert render().pixelColor(450, 5).alpha() == 0, 'opacity zero must restore full transparency'
for mode in ('duet', 'scroll'):
    for perspective in (False, True):
        style.mode, style.perspective_enabled = mode, perspective
        style.background_opacity = 45
        style.word_wave = True
        canvas.set_sequence([line], 0, 250, snap=True)
        assert not render().isNull()
print('PASS: adjustable zoom settles correctly; timed staggered wave moves real glyphs, pauses and respects KRC gaps; zero amplitude; independent panel alpha, rounded corners and zero-opacity reset; both layouts and 3D')
