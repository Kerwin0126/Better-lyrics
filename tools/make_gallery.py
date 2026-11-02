# Author: Kerwin
"""Capture the real widgets/renderer with original demo text and isolated settings.

python tools/make_gallery.py                 -> PNG screenshots and GIFs
python tools/make_gallery.py --native frosted -> Windows scene for native capture
python tools/make_gallery.py --native transparent
"""
import os,sys,time,math,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--native',choices=['frosted','transparent'])
args=parser.parse_args()
if not args.native:os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtCore import Qt,QRectF,QPointF,QTimer
from PySide6.QtGui import QImage,QPainter,QColor,QFont,QFontDatabase,QLinearGradient,QPen
from PySide6.QtWidgets import QApplication,QWidget
from unittest.mock import patch
from tempfile import TemporaryDirectory
import desktop_lyrics as ui
from lyric_data import LyricLine
from lyric_renderer import LyricCanvas

OUT=ROOT/'docs/images'
OUT.mkdir(parents=True,exist_ok=True)
TEXT=['晚风轻轻经过窗台','灯光落在琴弦之间','我们沿着熟悉的路走','把回声写进安静的夜',
      '听见远方传来一首歌','让时间慢一点流淌','把这一刻留在心上','每句歌词都带着微光',
      '夜色慢慢落在城市里','明天又是新的篇章','让音乐陪我们走远','故事还在继续生长',
      '等下一次与你相望','让这一首歌轻轻唱完','把微光留给每个平常']
LINES=[LyricLine(i*4500,4200,t,[(j*320,320,c) for j,c in enumerate(t)]) for i,t in enumerate(TEXT)]
app=QApplication([])
for font_name in ['msyh.ttc','msyhbd.ttc','segoeui.ttf','segoeuib.ttf','seguisym.ttf']:
    font_path=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/font_name
    if font_path.is_file():QFontDatabase.addApplicationFont(str(font_path))
app.setFont(QFont('Microsoft YaHei UI',10))

def background(w,h,title='',subtitle=''):
    image=QImage(w,h,QImage.Format.Format_ARGB32_Premultiplied)
    painter=QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient=QLinearGradient(0,0,w,h)
    gradient.setColorAt(0,QColor('#141829'));gradient.setColorAt(1,QColor('#343052'))
    painter.fillRect(image.rect(),gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#46416C'));painter.drawEllipse(QRectF(w*.7,-h*.35,w*.5,h*.9))
    painter.setBrush(QColor(81,152,158,35));painter.drawEllipse(QRectF(-w*.22,h*.55,w*.65,h*.8))
    painter.setPen(QColor('#F4F0FF'));painter.setFont(QFont('Microsoft YaHei UI',23,QFont.Weight.DemiBold))
    painter.drawText(QPointF(40,53),title)
    painter.setPen(QColor('#ADA8C4'));painter.setFont(QFont('Microsoft YaHei UI',11))
    painter.drawText(QPointF(42,83),subtitle)
    painter.setFont(QFont('Segoe UI',10));painter.drawText(QPointF(40,h-20),'BETTER LYRICS  /  浮词   ·   Kerwin')
    painter.end()
    return image

def canvas_for(style,w,h):
    canvas=LyricCanvas(style,preview=True)
    canvas.preview=False  # Same paint paths, without the studio preview decoration.
    canvas.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    canvas.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
    canvas.resize(w,h)
    return canvas

def layer(canvas,w,h,index=7,position=33400,snap=True):
    canvas.set_sequence(LINES,index,position,'微光 · 原创演示 / Kerwin',snap=snap)
    canvas.setMinimumSize(0,0);canvas.setMaximumSize(16777215,16777215)
    canvas.resize(w,h)
    image=QImage(w,h,QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    canvas.render(image)
    return image

def paste(image,overlay,x,y):
    p=QPainter(image);p.drawImage(x,y,overlay);p.end()

def static_gallery():
    for name,mode,rows,w,h in [('duet','duet',2,980,420),('sidebar','scroll',10,760,840)]:
        a=ui.Appearance(mode=mode,line_count=rows,size=40 if mode=='duet' else 31,
            region_width=w-80,region_height=h-140,align='left',color='#9CE6D4',active_scale=125,
            inactive_opacity=52,motion='none',outline=False)
        canvas=canvas_for(a,w-80,h-140)
        frame=background(w,h,'双行悬浮' if mode=='duet' else '多行侧边','全透明文字 · 字词时间变色' if mode=='duet' else '10 行 · 左对齐 · 当前句放大 125%')
        paste(frame,layer(canvas,w-80,h-140),40,108)
        frame.save(str(OUT/(name+'.png')))
        canvas.close()

    frame=background(1320,1250,'近大远小，四向透视','独立控制方向与角度；关闭后恢复平面布局')
    p=QPainter(frame);p.setPen(QColor('#D4CCE9'));p.setFont(QFont('Microsoft YaHei UI',16))
    directions=[('left','左近右远'),('right','右近左远'),('top','上近下远'),('bottom','下近上远')]
    p.end()
    for i,(direction,label) in enumerate(directions):
        x=25+(i%2)*650;y=112+(i//2)*550
        a=ui.Appearance(mode='scroll',perspective_enabled=True,perspective_direction=direction,
            perspective_angle=48,line_count=7,size=31,region_width=660,region_height=620,
            color='#C8B3FF',active_scale=126,outline=False,motion='none',inactive_opacity=58)
        c=canvas_for(a,620,490)
        paste(frame,layer(c,620,490),x,y+32)
        p=QPainter(frame);p.setPen(QColor('#DDD5F1'));p.setFont(QFont('Microsoft YaHei UI',15))
        p.drawText(QPointF(x+30,y+22),label+' · 48°');p.end();c.close()
    frame.save(str(OUT/'perspective.png'))

    frame=background(1320,700,'同一句歌词，不同的性格','已唱、未唱与其他行可以分别配色')
    for i,(alignment,color,label) in enumerate([('left','#8FF0CE','左对齐 · 薄荷'),('center','#C4ACFF','居中 · 雾紫'),('right','#FFBE91','右对齐 · 落日')]):
        a=ui.Appearance(mode='scroll',line_count=6,size=25,region_width=440,region_height=560,
            align=alignment,color=color,active_scale=125,outline=False,motion='none',inactive_opacity=58)
        c=canvas_for(a,420,510);paste(frame,layer(c,420,510),10+440*i,135)
        p=QPainter(frame);p.setPen(QColor(color));p.setFont(QFont('Microsoft YaHei UI',14))
        p.drawText(QPointF(40+440*i,125),label);p.end();c.close()
    frame.save(str(OUT/'colors-alignment.png'))

def animations():
    from PIL import Image
    for name in ['focus','wave']:
        a=ui.Appearance(mode='scroll' if name=='focus' else 'duet',line_count=4,size=38,
            region_width=920,region_height=330,color='#A5E6DB',pending_color='#DDD8EB',outline=False,
            motion='focus',motion_strength=95,motion_duration=560,active_scale=130,
            word_wave=name=='wave',wave_strength=100,wave_speed=100)
        c=canvas_for(a,920,330)
        frames=[]
        with patch('lyric_renderer.time.monotonic',return_value=100.0) as clock:
            for f in range(120):
                t=f/20;clock.return_value=100+t
                if name=='focus':index=5+int(t//1.5);position=index*4500+(t%1.5)/1.5*3500
                else:index=7;position=31500+(t%3)*1200
                frame=background(1000,470,'柔和放大' if name=='focus' else '字词波浪浮动',
                    '进入强度与时长可调' if name=='focus' else '按实际字词时间浮动，可与放大叠加')
                paste(frame,layer(c,920,330,index,position,snap=f==0),40,108)
                converted=frame.convertToFormat(QImage.Format.Format_RGBA8888)
                data=bytes(converted.bits())
                im=Image.frombytes('RGBA',(1000,470),data).convert('RGB').quantize(colors=128)
                frames.append(im)
        frames[0].save(OUT/(name+'.gif'),save_all=True,append_images=frames[1:],duration=50,loop=0,optimize=True,disposal=2)
        c.close()

def studio_screens():
    class DemoReader:
        def set_player(self,p):pass
        def statuses(self):return {}
        def snapshot(self):return dict(ok=False,error='原创演示'),time.monotonic()
        def close(self):pass
    with TemporaryDirectory() as folder,patch.object(ui,'BASE',Path(folder)),patch.object(ui,'SETTINGS',Path(folder)/'appearance.json'),patch.object(ui,'PlaybackSource',DemoReader),patch.object(ui,'discover_folder',lambda:Path(folder)),patch.object(ui.Appearance,'load',classmethod(lambda cls:cls(color='#C4ACFF',size=31,perspective_enabled=False))),patch.object(ui.Appearance,'save',lambda self:None):
        studio=ui.Studio();studio.timer.stop();studio.save_timer.stop();studio.overlay.hide()
        studio.lines=LINES;studio.track_title.setText('微光 · 原创演示');studio.track_artist.setText('Kerwin')
        studio.sync_detail.setText('原创演示数据 · 不代表真实播放器连接')
        studio.clock.setText('00:33 / 01:07');studio.footer.setText('演示预览 · 原创文字 · 真实渲染器')
        for key,item in studio.player_status_labels.items():item.setText(ui.PLAYERS[key]+' · 演示')
        studio.preview.set_sequence(LINES,7,33400,'微光 · 原创演示 / Kerwin',snap=True)
        studio.resize(1120,730);studio.show();app.processEvents();studio.grab().save(str(OUT/'studio.png'))
        studio.set_page(2);app.processEvents();studio.grab().save(str(OUT/'about.png'))
        studio.quit()

class NativeBoard(QWidget):
    def paintEvent(self,event):
        p=QPainter(self);p.drawImage(0,0,background(self.width(),self.height()))
        p.setFont(QFont('Microsoft YaHei UI',42,QFont.Weight.Bold))
        p.setPen(QColor(180,175,211,80))
        for y in range(80,self.height(),100):
            for x in range(20,self.width(),180):p.drawText(QPointF(x,y),'微 光')
        p.end()

if args.native:
    board=NativeBoard();board.setWindowTitle('Better lyrics · 原创演示背景')
    board.setWindowFlags(Qt.WindowType.Window|Qt.WindowType.WindowStaysOnTopHint)
    board.resize(1400,1000)
    area=app.primaryScreen().availableGeometry();board.move(area.center()-board.rect().center());board.show()
    a=ui.Appearance(mode='scroll',line_count=7,size=34,region_width=920,region_height=650,
        color='#C4ACFF',outline=False,motion='none',background_opacity=38 if args.native=='frosted' else 0,
        background_radius=46,background_blur=args.native=='frosted',locked=False,active_scale=126)
    c=LyricCanvas(a)
    c.setWindowFlags(Qt.WindowType.Window|Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
    c.setWindowTitle('Better lyrics · 演示截图 · '+args.native)
    c.resize(920,650);c.move(board.x()+240,board.y()+170)
    c.set_sequence(LINES,7,33400,'原创演示 / Kerwin',snap=True);c.show()
    QTimer.singleShot(180000,app.quit)
    sys.exit(app.exec())
else:
    static_gallery();animations();studio_screens()
    print('Gallery saved:',OUT)
