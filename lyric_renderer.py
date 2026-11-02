# Author: Kerwin
"""Transparent lyric layout, projective geometry and timed karaoke painting."""
from __future__ import annotations
import math
import time
from functools import lru_cache
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QLinearGradient, QPainter,
                          QPainterPath, QPen, QPolygonF, QTextLayout, QTextOption, QTransform,
                          QImage, QBitmap, QRegion)
from PySide6.QtWidgets import QWidget, QMenu
from native_backdrop import set_blur, close_blur


def entry_zoom(weight, strength):
    """Controllable entrance zoom, settling at exactly the configured final size."""
    weight = max(0, min(1, weight))
    amount = max(0, min(100, strength)) / 100
    return 1 - .28 * amount * (1 - weight) + .10 * amount * math.sin(math.pi * weight)


def wave_offset(phase, character, strength, speed):
    """A staggered wave which returns to baseline at both token boundaries."""
    phase = max(0, min(1, phase))
    return -24 * strength / 100 * math.sin(math.pi * phase) * math.sin(
        2 * math.pi * phase * speed / 100 - character * .85)


def clamp_ink_position(position, ink, area):
    """Keep visible glyphs on screen; transparent window margins may leave it."""
    x = max(area.left() - ink.left(), min(position.x(), area.right() + 1 - ink.right()))
    y = max(area.top() - ink.top(), min(position.y(), area.bottom() + 1 - ink.bottom()))
    return QPoint(round(x), round(y))


@lru_cache(maxsize=512)
def glyph_geometry(text, font_key):
    font = QFont()
    font.fromString(font_key)
    metrics = QFontMetricsF(font)
    path = QPainterPath()
    path.addText(QPointF(0, 0), font, text)
    advances = tuple(metrics.horizontalAdvance(text[:i]) for i in range(len(text) + 1))
    return path, advances, metrics.ascent(), metrics.descent(), metrics.height()


@lru_cache(maxsize=192)
def glyph_bitmap(text, font_key, color_name, outlined, dpr, halo=False):
    path, advances, ascent, descent, height = glyph_geometry(text, font_key)
    bounds = path.boundingRect().adjusted(-3, -3, 3, 3)
    image = QImage(max(1, math.ceil(bounds.width() * dpr)), max(1, math.ceil(bounds.height() * dpr)),
                   QImage.Format.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(dpr)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(-bounds.left(), -bounds.top())
    painter.setPen(QPen(QColor(color_name) if halo else QColor('#C7080A14'), 5.0 if halo else 2.2,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin) if outlined or halo else Qt.PenStyle.NoPen)
    painter.setBrush(Qt.BrushStyle.NoBrush if halo else QColor(color_name))
    painter.drawPath(path)
    painter.end()
    return image, bounds


def wrapped_lines(text, font, width):
    layout = QTextLayout(text, font)
    option = QTextOption()
    option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    layout.setTextOption(option)
    output = []
    layout.beginLayout()
    while True:
        line = layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(max(40, width))
        output.append(text[line.textStart():line.textStart() + line.textLength()].strip())
    layout.endLayout()
    return output or ['']


def played_characters(line, position_ms, next_start=None):
    """Continuous prefix length, using actual KRC token intervals when present."""
    local = position_ms - line.start_ms
    if local <= 0:
        return 0.0
    if line.words and ''.join(token[2] for token in line.words) == line.text:
        done = 0
        for start, duration, text in line.words:
            if local < start:
                return float(done)
            if duration > 0 and local < start + duration:
                return done + len(text) * max(0, min(1, (local - start) / duration))
            done += len(text)
        return float(len(line.text))
    duration = line.duration_ms or (next_start - line.start_ms if next_start else 5000)
    return len(line.text) * max(0, min(1, local / max(1, duration)))


def prefix_width(text, count, metrics):
    count = max(0.0, min(len(text), count))
    whole = int(count)
    before = metrics.horizontalAdvance(text[:whole])
    after = metrics.horizontalAdvance(text[:min(len(text), whole + 1)])
    return before + (after - before) * (count - whole)


def singing_span(line, position_ms, next_start=None):
    local = position_ms - line.start_ms
    if line.words and ''.join(token[2] for token in line.words) == line.text:
        count = 0
        for start, duration, text in line.words:
            if duration > 0 and start <= local < start + duration:
                return count, count + len(text), (local - start) / duration
            count += len(text)
        return None
    count = played_characters(line, position_ms, next_start)
    return (int(count), int(count) + 1, count % 1) if 0 < count < len(line.text) else None


def perspective_transform(width, height, target, direction, angle, roll=0):
    return cached_projection(width, height, target.x(), target.y(), target.width(), target.height(), direction, angle, roll)


@lru_cache(maxsize=64)
def cached_projection(width, height, tx, ty, tw, th, direction, angle, roll):
    """Project one text plane through a pinhole camera, then fit its quad."""
    target = QRectF(tx, ty, tw, th)
    source = QPolygonF([QPointF(0, 0), QPointF(width, 0), QPointF(width, height), QPointF(0, height)])
    angle = math.radians(max(0, min(65, angle)))
    yaw = (-angle if direction == 'left' else angle if direction == 'right' else 0)
    pitch = (angle if direction == 'top' else -angle if direction == 'bottom' else 0)
    spin = math.radians(roll)
    distance = max(width, height) * 1.1
    projected = []
    for point in source:
        x, y = point.x() - width / 2, point.y() - height / 2
        x, z = x * math.cos(yaw), -x * math.sin(yaw)
        y, z = y * math.cos(pitch) - z * math.sin(pitch), y * math.sin(pitch) + z * math.cos(pitch)
        x, y = x * math.cos(spin) - y * math.sin(spin), x * math.sin(spin) + y * math.cos(spin)
        scale = distance / (distance + z)
        projected.append(QPointF(x * scale, y * scale))
    bounds = QPolygonF(projected).boundingRect()
    scale = min(target.width() / max(1, bounds.width()), target.height() / max(1, bounds.height()))
    center = target.center()
    quad = QPolygonF([QPointF(center.x() + (p.x() - bounds.center().x()) * scale,
                             center.y() + (p.y() - bounds.center().y()) * scale) for p in projected])
    transform = QTransform()
    if not QTransform.quadToQuad(source, quad, transform):
        return QTransform()
    return transform


class LyricCanvas(QWidget):
    open_settings = Signal()
    moved = Signal()

    def __init__(self, appearance, preview=False):
        super().__init__()
        self.appearance, self.preview = appearance, preview
        self.current, self.upcoming = '等待音乐播放…', ''
        self.track = '音乐响起，歌词就会出现在这里'
        self.lines = []
        self.active_index = -1
        self.position_ms = 0
        self.origin_from = self.origin_to = 0.0
        self.animation_start = 0.0
        self.focus_start = 0.0
        self.focus_from = {}
        self.last_preview_update = 0.0
        self.drag_origin = None
        self.backdrop_key = None
        self.native_blur_active = False
        self.syncing_backdrop = False
        if preview:
            self.setMinimumHeight(270)
        else:
            self.setWindowTitle('浮词 · 透明桌面歌词')
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            self.apply_flags()
            self.setCursor(Qt.CursorShape.SizeAllCursor)

    def apply_flags(self):
        if self.preview:
            return
        visible, pos = self.isVisible(), self.pos()
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus
        if self.appearance.topmost:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        if self.appearance.locked:
            flags |= Qt.WindowType.WindowTransparentForInput
        self.setWindowFlags(flags)
        self.move(pos)
        if visible:
            self.show()
        self.sync_backdrop()

    def sync_backdrop(self):
        if self.preview or self.syncing_backdrop:
            return
        from PySide6.QtWidgets import QApplication
        if QApplication.platformName() != 'windows':
            return
        self.syncing_backdrop = True
        try:
            a = self.appearance
            hwnd = int(self.winId())
            panel = a.background_opacity > 0
            enabled = panel and a.background_blur
            key = (hwnd, panel, enabled, a.background_radius, self.width(), self.height(), self.devicePixelRatioF(), self.x(), self.y(), self.isVisible(), a.topmost)
            if key == self.backdrop_key:
                return
            self.backdrop_key = key
            if panel:
                path = QPainterPath()
                path.addRoundedRect(QRectF(self.rect()), a.background_radius, a.background_radius)
                self.setMask(QRegion(path.toFillPolygon().toPolygon()))
            else:
                self.clearMask()
            dpr = self.devicePixelRatioF()
            self.native_blur_active = set_blur(hwnd, enabled and self.isVisible(),
                round(self.width() * dpr) if panel else 0,
                round(self.height() * dpr) if panel else 0,
                round(a.background_radius * dpr), round(self.x() * dpr), round(self.y() * dpr), a.topmost) and enabled and self.isVisible()
        finally:
            self.syncing_backdrop = False

    def showEvent(self, event):
        super().showEvent(event)
        self.sync_backdrop()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sync_backdrop()

    def moveEvent(self, event):
        super().moveEvent(event)
        self.sync_backdrop()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.sync_backdrop()

    def closeEvent(self, event):
        if not self.preview:
            close_blur()
        super().closeEvent(event)

    def set_content(self, current, upcoming='', track=''):
        self.lines = []
        self.current, self.upcoming, self.track = current, upcoming, track
        self.update()

    def origin(self):
        duration = self.appearance.motion_duration / 1000
        fraction = min(1.0, max(0.0, (time.monotonic() - self.animation_start) / duration))
        return self.origin_from + (self.origin_to - self.origin_from) * (1 - (1 - fraction) ** 3)

    def focus_weights(self):
        if self.appearance.motion == 'none':
            return {self.active_index: 1.0}
        fraction = min(1.0, max(0.0, (time.monotonic() - self.focus_start) / (self.appearance.motion_duration / 1000)))
        eased = 1 - (1 - fraction) ** 3
        weights = {index: weight * (1 - eased) for index, weight in self.focus_from.items()}
        weights[self.active_index] = weights.get(self.active_index, 0) + eased
        return weights

    def animating(self):
        until = max(self.focus_start, self.animation_start) + self.appearance.motion_duration / 1000
        return self.appearance.motion != 'none' and time.monotonic() < until

    def set_sequence(self, lines, index, position_ms, track='', snap=False):
        previous_text = self.current
        changed = lines is not self.lines
        index_changed = index != self.active_index
        if not changed and not index_changed and position_ms == self.position_ms and not self.animating():
            return
        if changed or snap:
            self.focus_from = {index: 1.0}
            self.focus_start = 0
        elif index_changed:
            self.focus_from = {i: w for i, w in self.focus_weights().items() if w > .001}
            self.focus_start = time.monotonic()
        target = max(0, min(max(0, index) - self.appearance.line_count // 2,
                            max(0, len(lines) - self.appearance.line_count)))
        if changed or snap or abs(target - self.origin_to) > 4 or self.appearance.motion == 'none':
            self.origin_from = self.origin_to = float(target)
        elif target != self.origin_to:
            self.origin_from = self.origin()
            self.origin_to = float(target)
        if target != self.origin_to or index != self.active_index or changed:
            self.animation_start = time.monotonic()
        self.lines, self.active_index = lines, index
        self.position_ms, self.track = position_ms, track
        self.current = lines[index].text if 0 <= index < len(lines) else '等待第一句…'
        self.upcoming = next((line.text for line in lines[index + 1:] if line.text.strip()), '') if lines else ''
        if self.appearance.mode == 'duet' and self.current != previous_text:
            self.refresh_appearance()
        now = time.monotonic()
        if not self.preview or now - self.last_preview_update >= 1 / 30:
            self.update()
            self.last_preview_update = now

    def text_font(self, scale=1):
        font = QFont(self.appearance.font)
        font.setPointSizeF(max(6.0, self.appearance.size * scale))
        font.setWeight(QFont.Weight.DemiBold if self.appearance.bold else QFont.Weight.Normal)
        return font

    def paint_path(self, painter, text, font, x, baseline, color, opacity=1.0, played=None, scale=1.0, glow=None):
        key = font.toString()
        dpr = max(1.0, self.devicePixelRatioF())
        image, bounds = glyph_bitmap(text, key, color, self.appearance.outline, dpr)
        painter.save()
        painter.translate(x, baseline)
        painter.scale(scale, scale)
        painter.setOpacity(max(0, min(1, self.appearance.opacity / 100 * opacity)))
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if glow and self.appearance.word_wave and self.appearance.wave_strength > 0:
            _, advances, ascent, descent, height = glyph_geometry(text, key)
            start, end, phase = glow
            start, end = max(0, min(len(text), start)), max(0, min(len(text), end))
            if end > start:
                # Reuse the complete shaped line bitmap; slice it at advances so
                # kerning and karaoke colors stay identical to the flat renderer.
                slices = [(bounds.left() - 2, advances[start], 0),
                          (advances[end], bounds.right() + 2, 0)]
                for index in range(start, end):
                    dy = wave_offset(phase, index - start, self.appearance.wave_strength, self.appearance.wave_speed)
                    slices.append((advances[index], advances[index + 1], dy))
                for left, right, dy in slices:
                    if right <= left:
                        continue
                    painter.save()
                    painter.setClipRect(QRectF(left, -ascent - 40, right - left, height + 80), Qt.ClipOperation.IntersectClip)
                    painter.translate(0, dy)
                    self.paint_glyph_layers(painter, text, key, color, dpr, played, glow)
                    painter.restore()
                painter.restore()
                return
        self.paint_glyph_layers(painter, text, key, color, dpr, played, glow)
        painter.restore()

    def paint_glyph_layers(self, painter, text, key, color, dpr, played, glow):
        image, bounds = glyph_bitmap(text, key, color, self.appearance.outline, dpr)
        painter.drawImage(bounds.topLeft(), image)
        if played is not None and self.appearance.karaoke and played > 0:
            path, advances, ascent, descent, height = glyph_geometry(text, key)
            count = max(0, min(len(text), played))
            whole = int(count)
            prefix = advances[whole] + (advances[min(len(text),whole+1)]-advances[whole]) * (count-whole)
            painter.save()
            painter.setClipRect(QRectF(-2, -ascent - 4, prefix + 2, height + 8), Qt.ClipOperation.IntersectClip)
            image, bounds = glyph_bitmap(text, key, self.appearance.color, False, dpr)
            painter.drawImage(bounds.topLeft(), image)
            painter.restore()
        if glow and self.appearance.word_glow and self.appearance.karaoke:
            start, end, phase = glow
            path, advances, ascent, descent, height = glyph_geometry(text, key)
            start, end = max(0, min(len(text), start)), max(0, min(len(text), end))
            if end > start:
                painter.save()
                painter.setClipRect(QRectF(advances[start] - 2, -ascent - 5,
                                          advances[end] - advances[start] + 4, height + 10), Qt.ClipOperation.IntersectClip)
                painter.setOpacity(self.appearance.opacity / 100 * .2 * math.sin(math.pi * phase))
                image, bounds = glyph_bitmap(text, key, self.appearance.color, False, dpr, True)
                painter.drawImage(bounds.topLeft(), image)
                painter.restore()

    def preview_background(self, painter):
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor('#171927'))
        gradient.setColorAt(1, QColor('#2E2849'))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(QRectF(self.rect()), 20, 20)
        painter.setBrush(QColor(148, 122, 239, 15))
        painter.drawEllipse(QRectF(self.width() - 180, -110, 320, 320))
        painter.setPen(QColor('#B9A8F0'))
        painter.setFont(QFont('Segoe UI', 9, QFont.Weight.DemiBold))
        painter.drawText(QPointF(24, 32), 'LIVE PREVIEW  /  实时预览')
        painter.setPen(QColor('#A7A4B9'))
        painter.setFont(QFont('Microsoft YaHei UI', 9))
        track = QFontMetricsF(painter.font()).elidedText(self.track, Qt.TextElideMode.ElideRight, self.width() - 48)
        painter.drawText(QPointF(24, self.height() - 22), track)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if self.preview:
            self.preview_background(painter)
        self.paint_panel(painter)
        if self.appearance.mode == 'duet' or not self.lines:
            self.paint_duet(painter)
        else:
            self.paint_list(painter)
        painter.end()

    def paint_panel(self, painter):
        a = self.appearance
        if a.background_opacity <= 0:
            return
        rect = QRectF(self.rect()).adjusted(.5, 42 if self.preview else .5, -.5, -38 if self.preview else -.5)
        radius = min(a.background_radius, rect.width() / 2, rect.height() / 2)
        color = QColor(a.background_color)
        color.setAlphaF(a.background_opacity / 100)
        painter.save()
        painter.setOpacity(1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, radius, radius)
        # Restrained glass highlight, tied to panel opacity. Text opacity is independent.
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, round(34 * a.background_opacity / 100)), 1))
        painter.drawRoundedRect(rect, radius, radius)
        painter.restore()

    def paint_list(self, painter):
        available = QRectF(self.rect()).adjusted(24, 50 if self.preview else 16, -24, -42 if self.preview else -16)
        width, height = self.appearance.region_width - 40, self.appearance.region_height - 40
        transform = perspective_transform(width, height, available,
            self.appearance.perspective_direction, self.appearance.perspective_angle if self.appearance.mode == 'perspective' or self.appearance.perspective_enabled else 0,
            self.appearance.roll if self.appearance.mode == 'perspective' or self.appearance.perspective_enabled else 0)
        painter.save()
        painter.setClipRect(available)
        painter.setWorldTransform(transform, combine=True)
        count = self.appearance.line_count
        font = self.text_font()
        step = QFontMetricsF(font).height() * self.appearance.line_spacing / 100
        scale = min(1, height / (step * count + 10))
        font = self.text_font(scale)
        step *= scale
        block_height = step * count
        top = 4 if self.appearance.vertical == 'top' else height - block_height - 4 if self.appearance.vertical == 'bottom' else (height - block_height) / 2
        painter.setClipRect(QRectF(0, top, width, block_height), Qt.ClipOperation.IntersectClip)
        origin = self.origin()
        weights = self.focus_weights()
        for index in range(max(0, math.floor(origin) - 1), min(len(self.lines), math.ceil(origin) + count + 1)):
            line = self.lines[index]
            active = index == self.active_index
            weight = weights.get(index, 0.0)
            item_scale = 1 + (self.appearance.active_scale / 100 - 1) * weight
            if active and self.appearance.motion != 'none':
                item_scale *= entry_zoom(weight, self.appearance.motion_strength)
            item_font = self.text_font(scale)
            metrics = QFontMetricsF(item_font)
            advance = metrics.horizontalAdvance(line.text)
            # A list entry always occupies a single row; long text scales to fit.
            max_scale = self.appearance.active_scale / 100 * 1.04
            if advance * max_scale > width - 24:
                item_font.setPointSizeF(item_font.pointSizeF() * (width - 24) / (advance * max_scale))
                metrics = QFontMetricsF(item_font)
                advance = metrics.horizontalAdvance(line.text)
            advance *= item_scale
            x = 12 if self.appearance.align == 'left' else width - 12 - advance if self.appearance.align == 'right' else (width - advance) / 2
            baseline = top + (index - origin + .5) * step + (metrics.ascent() - metrics.descent()) * item_scale / 2
            if active and self.appearance.motion == 'float':
                baseline += 16 * self.appearance.motion_strength / 100 * (1 - weight)
            color = (self.appearance.pending_color if self.appearance.karaoke else self.appearance.color) if active else self.appearance.context_color
            progress = played_characters(line, self.position_ms, self.lines[index + 1].start_ms if index + 1 < len(self.lines) else None) if active else None
            glow = singing_span(line, self.position_ms, self.lines[index + 1].start_ms if index + 1 < len(self.lines) else None) if active else None
            self.paint_path(painter, line.text, item_font, x, baseline, color,
                            self.appearance.inactive_opacity / 100 + (1 - self.appearance.inactive_opacity / 100) * weight,
                            progress, item_scale, glow)
        painter.restore()

    def paint_duet(self, painter):
        font = self.text_font(min(1, 30 / self.appearance.size) if self.preview else 1)
        metrics = QFontMetricsF(font)
        rows = wrapped_lines(self.current, font, self.width() - 56)
        next_font = QFont(font)
        next_font.setPointSizeF(max(10, font.pointSizeF() * .55))
        next_metrics = QFontMetricsF(next_font)
        next_rows = wrapped_lines(self.upcoming, next_font, self.width() - 64) if self.appearance.next_line and self.upcoming else []
        step, next_step = metrics.height() * 1.18, next_metrics.height() * 1.2
        height = len(rows) * step + (14 + len(next_rows) * next_step if next_rows else 0)
        baseline = (self.height() - height) / 2 + metrics.ascent()
        line = self.lines[self.active_index] if 0 <= self.active_index < len(self.lines) else None
        progress = played_characters(line, self.position_ms,
            self.lines[self.active_index + 1].start_ms if self.active_index + 1 < len(self.lines) else None) if line else None
        glow = singing_span(line, self.position_ms,
            self.lines[self.active_index + 1].start_ms if self.active_index + 1 < len(self.lines) else None) if line else None
        consumed = 0
        focus = self.focus_weights().get(self.active_index, 1.0)
        entry_scale = 1.0 if self.appearance.motion == 'none' or not self.lines else entry_zoom(focus, self.appearance.motion_strength)
        entry_opacity = 1.0 if not self.lines else .65 + .35 * focus
        for row in rows:
            x = (self.width() - metrics.horizontalAdvance(row) * entry_scale) / 2
            color = self.appearance.pending_color if progress is not None and self.appearance.karaoke else self.appearance.color
            row_start = self.current.find(row, consumed)
            row_start = consumed if row_start < 0 else row_start
            lift = 16 * self.appearance.motion_strength / 100 * (1-focus) if self.appearance.motion == 'float' and self.lines else 0
            row_glow = (glow[0] - row_start, glow[1] - row_start, glow[2]) if glow and glow[0] < row_start + len(row) and glow[1] > row_start else None
            self.paint_path(painter, row, font, x, baseline + lift, color, entry_opacity,
                            played=max(0, progress - row_start) if progress is not None else None, scale=entry_scale, glow=row_glow)
            consumed = row_start + len(row)
            baseline += step
        if next_rows:
            baseline += 12 + next_metrics.ascent() - metrics.ascent()
            for row in next_rows:
                self.paint_path(painter, row, next_font, (self.width() - next_metrics.horizontalAdvance(row)) / 2,
                                baseline, self.appearance.context_color, self.appearance.inactive_opacity / 100)
                baseline += next_step

    def refresh_appearance(self):
        if not self.preview:
            screen = self.screen().availableGeometry()
            if self.appearance.mode != 'duet':
                self.resize(min(self.appearance.region_width, screen.width() - 40), min(self.appearance.region_height, screen.height() - 40))
            else:
                width = min(1260, screen.width() - 40)
                font = self.text_font()
                rows = wrapped_lines(self.current, font, width - 56)
                height = len(rows) * QFontMetricsF(font).height() * 1.18 + (50 if self.appearance.next_line else 0) + 56
                self.resize(width, min(max(135, math.ceil(height)), screen.height()))
        self.origin_from = self.origin_to = float(max(0, min(max(0, self.active_index) - self.appearance.line_count // 2,
                                                   max(0, len(self.lines) - self.appearance.line_count))))
        self.sync_backdrop()
        self.update()

    def mousePressEvent(self, event):
        if not self.preview and event.button() == Qt.MouseButton.LeftButton:
            self.drag_origin = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def visible_ink_bounds(self):
        # Measure native alpha only on drag release/explicit repositioning.
        image = QImage(self.size(), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        self.render(image)
        return QRectF(QRegion(QBitmap.fromImage(image.createAlphaMask())).boundingRect())

    def mouseMoveEvent(self, event):
        if self.drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_origin)

    def mouseReleaseEvent(self, event):
        if self.drag_origin is not None:
            self.drag_origin = None
            self.moved.emit()

    def mouseDoubleClickEvent(self, event):
        if not self.preview:
            self.open_settings.emit()

    def contextMenuEvent(self, event):
        if not self.preview:
            menu = QMenu(self)
            menu.addAction('打开浮词设置', self.open_settings.emit)
            menu.exec(event.globalPos())


class PlaybackClock:
    """Bounded interpolation of coarse media timestamps, never an audio recognizer."""
    def __init__(self):
        self.identity = None
        self.raw = self.base = self.updated = self.last_received = 0.0
        self.state = 'paused'
        self.duration = 0
        self.seek = False
        self.rate = 1.0

    def position(self, now):
        advance = max(0, now - self.updated) * 1000 * self.rate if self.state == 'playing' else 0
        value = min(self.base + advance, self.raw + 1500) if self.state == 'playing' else self.base
        return max(0, min(value, self.duration or value))

    def accept(self, data, received):
        if received == self.last_received:
            return
        raw, identity, state = data['position_ms'], data['identity'], data['state']
        previous = self.position(received)
        changed = identity != self.identity
        self.seek = changed or abs(raw - previous) > 1600 or raw < self.raw - 100
        if changed or self.seek:
            self.base = raw
            self.updated = received
            self.rate = 1.0
        elif state == 'paused':
            self.base = (previous if raw == self.raw else raw) if self.state == 'paused' else max(raw, min(raw + 999, previous))
            self.updated = received
        elif state != self.state:
            self.base, self.updated = raw, received
            self.rate = 1.0
        elif raw != self.raw:
            # The second boundary occurred between two samples; use its midpoint.
            lag = min(250, max(0, (received - self.last_received) * 500))
            error = raw + lag - previous
            self.base, self.updated = previous, received
            self.rate = 1 + max(-.18, min(.18, error / 2000))
        self.raw, self.identity, self.state = raw, identity, state
        self.last_received, self.duration = received, data.get('duration_ms', 0)
