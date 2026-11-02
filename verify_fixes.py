# Author: Kerwin
"""Regression checks for edge placement, independent layouts and effect toggle."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
import desktop_lyrics as ui
from lyric_renderer import glyph_bitmap, PlaybackClock
from lyrics_viewer import LyricLine

app=QApplication([])
for name in ('msyh.ttc','msyhbd.ttc'):
    QFontDatabase.addApplicationFont(str(Path('C:/Windows/Fonts')/name))
class DummyReader:
    def snapshot(self): return None,0
    def close(self): pass
ui.PlaybackSource=DummyReader
ui.Appearance.load=classmethod(lambda cls: cls(mode='scroll',perspective_enabled=True,locked=False))
ui.Appearance.save=lambda self: None
studio=ui.Studio()
studio.timer.stop()
studio.save_timer.stop()
studio.lines=[LyricLine(i*4000,3600,'这是一句测试歌词 沿着风的方向',[]) for i in range(30)]
studio.render_position(15,61500,True)
ink=studio.overlay.visible_ink_bounds()
assert ink.left()>10,ink
studio.overlay.move(-round(ink.left()),100)
studio.save_position()
assert studio.overlay.x()<0, '透明留白应该允许移出屏幕'
assert abs(studio.overlay.x()+studio.overlay.visible_ink_bounds().left())<=2
left=studio.overlay.x()
studio.change('locked',True)
studio.change('locked',False)
assert studio.overlay.x()==left,'鼠标穿透切换不应拉回窗口'
studio.change('perspective_enabled',False)
assert studio.appearance.mode=='scroll' and not studio.appearance.perspective_enabled
assert abs(studio.overlay.x()+studio.overlay.visible_ink_bounds().left())<=2, '关闭3D后保留文字的贴边位置'
studio.change('perspective_enabled',True)
assert studio.appearance.mode=='scroll' and studio.appearance.perspective_enabled
assert abs(studio.overlay.x()+studio.overlay.visible_ink_bounds().left())<=2
sidebar_position=studio.overlay.pos()
studio.change('mode','duet')
assert studio.appearance.mode=='duet' and studio.appearance.perspective_enabled
studio.overlay.move(10,50)
studio.save_position()
duet_position=studio.overlay.pos()
studio.change('mode','scroll')
assert studio.overlay.pos()==sidebar_position,'侧边版的位置没有恢复'
studio.change('mode','duet')
assert studio.overlay.pos()==duet_position,'双行版的位置没有恢复'
assert studio.control_widgets['mode'].count()==2
assert studio.checks['perspective_enabled'].isEnabled() is False
studio.change('mode','scroll')
studio.checks['perspective_enabled'].setChecked(False)
assert studio.appearance.perspective_enabled is False, '真实复选框没有关闭3D'
canvas=studio.overlay
canvas.set_sequence(studio.lines,15,61500,snap=True)
canvas.set_sequence(studio.lines,16,64000)
start=canvas.focus_weights().get(16,0)
canvas.focus_start-=studio.appearance.motion_duration/2000
middle=canvas.focus_weights().get(16,0)
canvas.focus_start-=studio.appearance.motion_duration/1000
end=canvas.focus_weights().get(16,0)
assert 0<=start<middle<end<=1
assert abs(sum(canvas.focus_weights().values())-1)<.001
canvas.visible_ink_bounds()
misses=glyph_bitmap.cache_info().misses
for position in range(64200,64800,40):
    canvas.set_sequence(studio.lines,16,position)
    canvas.visible_ink_bounds()
assert glyph_bitmap.cache_info().misses<=misses+2,'稳定绘制反复重建字形'
clock=PlaybackClock()
for tick in range(1,70):
    received=tick*.1
    raw=int(max(0,received-.13))*1000
    before=clock.position(received)
    clock.accept(dict(identity='test',position_ms=raw,state='playing',duration_ms=200000),received)
    after=clock.position(received)
    if not clock.seek: assert after>=before-.001,'正常播放时插值回退'
    assert after<=raw+1500
studio.quit()
print('PASS: text touches screen edge with negative window coordinates; lock/unlock stays put; 3D toggles both ways; duet/sidebar position memory; real checkbox; smooth focus transition; glyph cache reuse; monotonic bounded playhead')
