# Author: Kerwin
"""Original installer artwork, drawn with Qt rather than downloaded assets."""
import os,sys
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter,QLinearGradient,QColor,QFont,QFontDatabase,QPainterPath,QPen
from PySide6.QtCore import QRectF,Qt
ROOT=Path(__file__).resolve().parents[1]
app=QApplication([])
for name in ['msyh.ttc','msyhbd.ttc','segoeui.ttf','segoeuib.ttf']:
    QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name))
image=QImage(492,942,QImage.Format.Format_RGB32)
p=QPainter(image);p.setRenderHint(QPainter.RenderHint.Antialiasing)
gradient=QLinearGradient(0,0,492,942);gradient.setColorAt(0,QColor('#1C2034'));gradient.setColorAt(1,QColor('#534575'))
p.fillRect(image.rect(),gradient)
p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#74609F'));p.drawEllipse(QRectF(190,-170,520,520))
p.setBrush(QColor(158,220,203,20));p.drawEllipse(QRectF(-240,600,650,650))
icon=QImage(str(ROOT/'assets/floating-lyrics.png'));p.drawImage(QRectF(46,80,160,160),icon)
font=QFont('Segoe UI');font.setPixelSize(58);font.setWeight(QFont.Weight.DemiBold);p.setFont(font);p.setPen(QColor('#F6F1FF'))
p.drawText(QRectF(48,300,410,160),Qt.AlignmentFlag.AlignLeft,'Better\nlyrics')
font=QFont('Microsoft YaHei UI');font.setPixelSize(66);font.setWeight(QFont.Weight.Bold);p.setFont(font)
p.drawText(QRectF(48,495,400,100),Qt.AlignmentFlag.AlignLeft,'浮词')
font.setPixelSize(26);font.setWeight(QFont.Weight.Normal);p.setFont(font);p.setPen(QColor('#D5CDE8'))
p.drawText(QRectF(48,615,390,160),Qt.TextFlag.TextWordWrap,'把歌词留在桌面\n把样子交给你')
p.setPen(QPen(QColor('#9EDDD0'),3))
path=QPainterPath();path.moveTo(48,805);path.cubicTo(140,745,245,870,425,795);p.drawPath(path)
font=QFont('Segoe UI');font.setPixelSize(23);p.setFont(font);p.setPen(QColor('#C8BADD'))
p.drawText(QRectF(48,875,400,40),Qt.AlignmentFlag.AlignLeft,'DESIGNED BY KERWIN')
p.end();image.save(str(ROOT/'assets/installer-sidebar.bmp'))
small=QImage(165,165,QImage.Format.Format_RGB32);small.fill(QColor('#FFFFFF'))
p=QPainter(small);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform);p.drawImage(QRectF(10,10,145,145),icon);p.end()
small.save(str(ROOT/'assets/installer-small.bmp'))
