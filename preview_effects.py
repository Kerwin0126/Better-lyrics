# Author: Kerwin
"""Isolated visual QA scene. Does not read/write user settings or control KuGou."""
import sys
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication, QWidget, QPushButton
from desktop_lyrics import Appearance
from lyric_renderer import LyricCanvas
from lyric_data import LyricLine

app = QApplication([])
class Backdrop(QWidget):
    def paintEvent(self, event):
        p = QPainter(self)
        for y in range(0, self.height(), 28):
            for x in range(0, self.width(), 28):
                p.fillRect(x, y, 28, 28, QColor('#D1CFDE') if (x//28+y//28)%2 else QColor('#5C5680'))
        p.setFont(QFont('Microsoft YaHei UI', 22))
        p.setPen(QColor('white'))
        p.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter, '背景图案用于检查真实磨砂模糊')
board = Backdrop()
board.setWindowTitle('浮词 · 磨砂测试底板')
board.resize(1000, 640)
board.move(700, 180)
board.show()
style = Appearance(mode='scroll', line_count=5, size=30, region_width=700, region_height=430,
    background_opacity=40, background_radius=80, motion='focus', motion_strength=75,
    word_wave=True, wave_strength=80, perspective_enabled=False, locked='--tool' in sys.argv)
canvas = LyricCanvas(style)
if '--tool' not in sys.argv:
    canvas.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
canvas.setWindowTitle('浮词 · 动效磨砂验证')
canvas.resize(700, 430)
canvas.move(850, 250)
lines = [LyricLine(i*4000, 4000, text, [(0,900,text[:2]),(900,1100,text[2:4]),(2000,2000,text[4:])])
    for i,text in enumerate(['晚风轻轻经过窗台','灯光落在琴弦之间','让每一个字随歌浮动','旋律沿着夜色流淌','把心事交给这一瞬间','我们一起听见明天','故事还会继续唱下去'])]
canvas.show()
tick = [0]
def advance():
    tick[0] = (tick[0]+17) % 28000
    canvas.set_sequence(lines, tick[0]//4000, tick[0])
timer=QTimer()
timer.timeout.connect(advance)
timer.start(17)
if '--check' in sys.argv:
    def check():
        assert canvas.native_blur_active, 'Windows compositor rejected the blur request'
        assert not canvas.mask().isEmpty()
        style.background_opacity=0
        canvas.refresh_appearance()
        assert not canvas.native_blur_active and canvas.mask().isEmpty()
        style.background_opacity=40
        canvas.refresh_appearance()
        assert canvas.native_blur_active and not canvas.mask().isEmpty()
        canvas.hide()
        assert not canvas.native_blur_active
        canvas.show()
        assert canvas.native_blur_active
        for radius in (0, 24, 80):
            style.background_radius = radius
            canvas.refresh_appearance()
            assert canvas.native_blur_active
        style.background_blur = False
        canvas.refresh_appearance()
        assert not canvas.native_blur_active
        style.background_blur = True
        canvas.refresh_appearance()
        canvas.move(canvas.x()+12,canvas.y()+12)
        assert canvas.native_blur_active
        print('PASS: native blur accepted; opacity zero removes backdrop and mask; re-enable, hide/show, 0/24/80 radius, blur toggle and movement work. Inspect checkerboard corners for compositor clipping.',flush=True)
    QTimer.singleShot(150, check)
sys.exit(app.exec())
