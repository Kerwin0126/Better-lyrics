# Author: Kerwin
"""CPU paint benchmark; excludes the Windows compositor and physical display."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import statistics
import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QFontDatabase
from PySide6.QtCore import Qt
from desktop_lyrics import Appearance
from lyric_renderer import LyricCanvas
from lyrics_viewer import LyricLine
app=QApplication([])
for name in ('msyh.ttc','msyhbd.ttc'):
    QFontDatabase.addApplicationFont(str(Path('C:/Windows/Fonts')/name))
lines=[LyricLine(i*4000,3600,'晚风经过窗台 音乐正在慢慢流淌',[]) for i in range(30)]
for mode in ('scroll','perspective'):
    style=Appearance(mode=mode, word_wave='--effects' in sys.argv,
                     wave_strength=100, background_opacity=40 if '--effects' in sys.argv else 0)
    canvases=[LyricCanvas(style),LyricCanvas(style,True)]
    canvases[0].resize(700,760)
    canvases[1].resize(640,370)
    buffers=[QImage(c.size(),QImage.Format.Format_ARGB32_Premultiplied) for c in canvases]
    timings=[]
    for frame in range(80):
        started=time.perf_counter()
        for c,buffer in zip(canvases,buffers):
            c.set_sequence(lines,15,60000+frame*16,snap=frame==0)
            buffer.fill(Qt.GlobalColor.transparent)
            c.render(buffer)
        timings.append((time.perf_counter()-started)*1000)
    print(mode, 'combined median_ms',round(statistics.median(timings[10:]),2),
          'p95_ms',round(sorted(timings[10:])[int(len(timings[10:])*.95)],2))
