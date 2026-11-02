# Author: Kerwin
"""Behavioral checks for timing, row count, projective direction and transparency."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QFontDatabase
from PySide6.QtCore import QPointF, QRectF, Qt
from desktop_lyrics import Appearance
from lyrics_viewer import LyricLine
from lyric_renderer import LyricCanvas, PlaybackClock, played_characters, perspective_transform

app = QApplication([])
for name in ('msyh.ttc','msyhbd.ttc'):
    font_file=Path('C:/Windows/Fonts') / name
    if font_file.is_file(): QFontDatabase.addApplicationFont(str(font_file))
line = LyricLine(1000, 1300, 'AB中D', [(0,100,'A'),(100,900,'B'),(1100,100,'中'),(1200,0,'D')])
assert played_characters(line, 999) == 0
assert played_characters(line, 1050) == .5
assert 1 < played_characters(line, 1200) < 1.2
assert played_characters(line, 2050) == 2  # The gap does not color the next syllable early.
assert played_characters(line, 2150) == 2.5
assert played_characters(line, 2200) == 4
assert played_characters(LyricLine(0,None,'ABCD',[]),1000,2000) == 2

clock = PlaybackClock()
def sample(pos, state, at, identity='test'):
    clock.accept(dict(identity=identity, position_ms=pos, state=state, duration_ms=90000), at)
sample(0,'playing',10)
assert 199 < clock.position(10.2) < 201
sample(1000,'playing',11.1)
sample(1000,'paused',11.5)
held = clock.position(12)
sample(1000,'paused',11.8)
assert clock.position(15) == held
sample(0,'paused',12.2)
assert clock.seek and clock.position(20) == 0
sample(4000,'playing',21,'another song')
assert clock.seek and clock.position(40) <= 5500

for direction in ('left','right','top','bottom'):
    transform = perspective_transform(600,600,QRectF(0,0,600,600),direction,45)
    assert transform.isInvertible() and not transform.isAffine()
    points=[transform.map(QPointF(x,y)) for x,y in [(0,0),(600,0),(600,600),(0,600)]]
    length=lambda a,b: ((a.x()-b.x())**2+(a.y()-b.y())**2)**.5
    if direction=='left': assert length(points[0],points[3]) > length(points[1],points[2])
    if direction=='right': assert length(points[0],points[3]) < length(points[1],points[2])
    if direction=='top': assert length(points[0],points[1]) > length(points[3],points[2])
    if direction=='bottom': assert length(points[0],points[1]) < length(points[3],points[2])

lines=[LyricLine(i*4000,3200,'MMMMMMMM',[(j*400,400,'M') for j in range(8)]) for i in range(30)]
a=Appearance(mode='scroll',line_count=10,region_width=700,region_height=760,outline=False,
             color='#8FF0CE',pending_color='#FFBE91',context_color='#C4ACFF',inactive_opacity=70)
canvas=LyricCanvas(a)
canvas.refresh_appearance()
canvas.set_sequence(lines,15,61600,snap=True)
image=QImage(canvas.size(),QImage.Format.Format_ARGB32)
image.fill(Qt.GlobalColor.transparent)
canvas.render(image)
ink_rows=[y for y in range(image.height()) if any(image.pixelColor(x,y).alpha()>10 for x in range(image.width()))]
groups=[]
for y in ink_rows:
    if not groups or y>groups[-1][-1]+1: groups.append([y])
    else: groups[-1].append(y)
assert len(groups)==10, ('visible line count',len(groups))
assert image.pixelColor(0,0).alpha()==0
colors={image.pixelColor(x,y).name().upper() for y in ink_rows for x in range(image.width()) if image.pixelColor(x,y).alpha()>100}
assert '#8FF0CE' in colors and '#FFBE91' in colors
for count in (1,6,24):
    a.line_count=count
    canvas.refresh_appearance()
    canvas.set_sequence(lines,15,61600,snap=True)
    canvas.render(image)
for direction in ('left','right','top','bottom'):
    a.mode='perspective'
    a.perspective_direction=direction
    a.roll=20
    canvas.render(image)

# A visual contact sheet uses original sample text, without exporting cached lyrics.
samples=['晚风经过安静的窗台','街灯把影子轻轻拉长','我们沿着熟悉的路走','听见远方传来一首歌','让时间慢一点流淌',
         '把这一刻留在心上','每段旋律都有一个方向','每句歌词都带着微光','夜色慢慢落在城市里','明天又是新的篇章',
         '让音乐陪我们走远','故事还在继续生长','我把回声写进了风里','等下一次与你相望','让这一首歌轻轻唱完']
demo=[LyricLine(i*4000,3600,t,[(j*200,200,c) for j,c in enumerate(t)]) for i,t in enumerate(samples)]
gallery=QImage(1200,720,QImage.Format.Format_ARGB32)
gallery.fill(QColor('#171927'))
painter=QPainter(gallery)
for i,(caption,mode,direction) in enumerate([('多行 · 左对齐','scroll','left'),('透视 · 左近右远','perspective','left'),('透视 · 上近下远','perspective','top')]):
    a=Appearance(mode=mode,line_count=10,region_width=650,region_height=900,size=32,color='#8FF0CE',perspective_direction=direction,perspective_angle=48)
    demo_canvas=LyricCanvas(a)
    demo_canvas.resize(400,640)
    demo_canvas.set_sequence(demo,7,28700,snap=True)
    frame=QImage(400,640,QImage.Format.Format_ARGB32)
    frame.fill(Qt.GlobalColor.transparent)
    demo_canvas.render(frame)
    painter.drawImage(i*400,60,frame)
    painter.setFont(QFont('Microsoft YaHei UI',14))
    painter.setPen(QColor('#E5DDF8'))
    painter.drawText(QRectF(i*400,10,400,40),Qt.AlignmentFlag.AlignCenter,caption)
painter.end()
gallery.save(str(Path(__file__).with_name('样式预览.png')))
print('PASS: irregular KRC token timings, gaps, LRC fallback, pause/seek/track reset, bounded interpolation, four true perspective directions, exactly 10 visible rows, two-color glyph fill, 1/6/24 rows, transparent background')
