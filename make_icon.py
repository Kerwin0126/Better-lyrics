# Author: Kerwin
"""Draw an original vector-style music/lyric icon and encode a multi-size ICO."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import struct
from PySide6.QtCore import Qt, QRectF, QPointF, QBuffer, QIODevice
from PySide6.QtGui import QImage, QPainter, QPainterPath, QLinearGradient, QColor, QPen
from PySide6.QtWidgets import QApplication

app = QApplication([])
assets = Path(__file__).resolve().parent / 'assets'
assets.mkdir(exist_ok=True)
image = QImage(512, 512, QImage.Format.Format_ARGB32_Premultiplied)
image.fill(Qt.GlobalColor.transparent)
p = QPainter(image)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
gradient = QLinearGradient(60, 0, 470, 512)
gradient.setColorAt(0, QColor('#B79BEF'))
gradient.setColorAt(.48, QColor('#8064C1'))
gradient.setColorAt(1, QColor('#43316E'))
p.setPen(Qt.PenStyle.NoPen)
p.setBrush(gradient)
p.drawRoundedRect(QRectF(8, 8, 496, 496), 120, 120)
clip = QPainterPath()
clip.addRoundedRect(QRectF(8, 8, 496, 496), 120, 120)
p.save()
p.setClipPath(clip)
p.setBrush(QColor(255, 255, 255, 18))
p.drawEllipse(QRectF(-90, -200, 620, 490))
p.restore()
# A rising music stem and its softly rounded flag.
note = QPainterPath()
note.moveTo(298, 300)
note.lineTo(298, 119)
note.cubicTo(298, 105, 308, 100, 320, 107)
note.lineTo(391, 146)
note.cubicTo(411, 158, 416, 179, 410, 200)
note.cubicTo(387, 181, 362, 168, 339, 162)
note.lineTo(339, 307)
note.cubicTo(339, 342, 306, 366, 271, 356)
note.cubicTo(241, 347, 243, 316, 264, 305)
note.cubicTo(274, 300, 286, 298, 298, 300)
p.setBrush(QColor('#FFF7E7'))
p.drawPath(note)
# Three floating lyric strokes, the current one warmer and brighter.
p.setPen(QPen(QColor('#EEE6FF'), 19, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
p.drawLine(QPointF(108, 209), QPointF(227, 209))
p.setPen(QPen(QColor('#FFD69A'), 22, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
wave = QPainterPath(QPointF(108, 272))
wave.cubicTo(142, 272, 148, 253, 176, 253)
wave.cubicTo(197, 253, 207, 263, 224, 263)
p.drawPath(wave)
p.setPen(QPen(QColor('#D3C4EA'), 17, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
p.drawLine(QPointF(108, 338), QPointF(195, 338))
p.end()
image.save(str(assets / 'floating-lyrics.png'))
pngs = []
sizes = (16, 24, 32, 48, 64, 128, 256)
for size in sizes:
    small = image.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    small.save(buffer, 'PNG')
    pngs.append(bytes(buffer.data()))
offset = 6 + 16 * len(sizes)
entries = []
for size, png in zip(sizes, pngs):
    entries.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(png), offset))
    offset += len(png)
(assets / 'floating-lyrics.ico').write_bytes(struct.pack('<HHH', 0, 1, len(sizes)) + b''.join(entries) + b''.join(pngs))
print('Created original PNG and 7-size ICO in', assets)
