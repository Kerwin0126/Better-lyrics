# Author: Kerwin
"""Transparent desktop lyrics and a separate appearance studio."""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import asdict, dataclass, fields, field
import hashlib
import json
import math
from pathlib import Path
import sys
import time

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import (QAction, QColor, QFont, QFontMetricsF, QIcon, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap, QTextLayout, QTextOption)
from PySide6.QtWidgets import (QApplication, QCheckBox, QColorDialog, QComboBox,
    QFileDialog, QFontComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QPushButton, QScrollArea, QSlider, QStackedWidget,
    QSystemTrayIcon, QTextBrowser, QVBoxLayout, QWidget, QRadioButton, QButtonGroup)

from lyric_data import decode_file, discover_folder, match_file, parse_lyrics, scan, short_name
from playback_source import PlaybackSource
from lyric_renderer import LyricCanvas, wrapped_lines, PlaybackClock
from studio_controls import build_controls
from app_paths import DATA_DIR, APP_ICON
from player_lyrics import PLAYERS, LyricProvider
from about_page import build_about_page

BASE = DATA_DIR
SETTINGS = BASE / 'appearance.json'


@dataclass
class Appearance:
    player: str = 'kugou'
    color: str = '#F4F0FF'
    font: str = 'Microsoft YaHei UI'
    size: int = 34
    opacity: int = 100
    bold: bool = True
    outline: bool = True
    next_line: bool = True
    topmost: bool = True
    locked: bool = False
    visible: bool = True
    x: int | None = None
    y: int | None = None
    mode: str = 'scroll'
    line_count: int = 10
    align: str = 'left'
    anchor: str = 'left'
    region_vertical: str = 'center'
    vertical: str = 'center'
    region_width: int = 760
    region_height: int = 760
    active_scale: int = 118
    line_spacing: int = 150
    inactive_opacity: int = 48
    pending_color: str = '#E5E1F0'
    context_color: str = '#CBD1E3'
    karaoke: bool = True
    perspective_direction: str = 'left'
    perspective_angle: int = 35
    roll: int = 0
    perspective_enabled: bool = False
    motion: str = 'float'
    motion_duration: int = 280
    motion_strength: int = 35
    word_wave: bool = False
    wave_strength: int = 45
    wave_speed: int = 100
    background_opacity: int = 0
    background_color: str = '#171B2A'
    background_radius: int = 24
    background_blur: bool = True
    fps: int = 60
    word_glow: bool = True
    positions: dict = field(default_factory=dict)

    @classmethod
    def load(cls):
        result = cls()
        try:
            values = json.loads(SETTINGS.read_text(encoding='utf-8'))
            for field in fields(cls):
                if field.name in values:
                    value = values[field.name]
                    old = getattr(result, field.name)
                    if (old is None and (value is None or type(value) is int)) or type(value) is type(old):
                        setattr(result, field.name, value)
            if 'mode' not in values:
                result.x = result.y = None
            if result.mode == 'perspective':
                result.mode = 'scroll'
                result.perspective_enabled = True
            for key, lower, upper in [('line_count',1,24), ('region_width',320,1600), ('region_height',240,1400),
                    ('active_scale',100,180), ('line_spacing',110,220), ('inactive_opacity',10,100),
                    ('perspective_angle',0,65), ('roll',-30,30), ('motion_duration',120,700),
                    ('motion_strength',0,100), ('wave_strength',0,100), ('wave_speed',50,200),
                    ('background_opacity',0,100), ('background_radius',0,80)]:
                setattr(result, key, max(lower, min(upper, getattr(result, key))))
            for key, allowed in [('player',tuple(PLAYERS)), ('mode', ('duet','scroll')), ('align', ('left','center','right')), ('motion', ('none','focus','float')),
                    ('anchor', ('left','center','right','custom')), ('vertical', ('top','center','bottom')),
                    ('region_vertical', ('top','center','bottom')), ('perspective_direction', ('left','right','top','bottom'))]:
                if getattr(result, key) not in allowed:
                    setattr(result, key, getattr(cls(), key))
            for key in ('pending_color', 'context_color', 'background_color'):
                if not QColor(getattr(result, key)).isValid():
                    setattr(result, key, getattr(cls(), key))
            result.size = max(20, min(68, result.size))
            result.opacity = max(20, min(100, result.opacity))
            result.fps = 60 if result.fps != 30 else 30
            valid_positions = {}
            for key, profile in result.positions.items():
                if key in ('duet','scroll') and isinstance(profile,dict):
                    x, y = profile.get('x'), profile.get('y')
                    if (x is None or type(x) is int) and (y is None or type(y) is int):
                        valid_positions[key] = dict(x=x, y=y,
                            anchor=profile.get('anchor') if profile.get('anchor') in ('left','right','center','custom') else 'center',
                            region_vertical=profile.get('region_vertical') if profile.get('region_vertical') in ('top','center','bottom') else 'center')
            result.positions = valid_positions
            if not QColor(result.color).isValid():
                result.color = cls().color
        except (OSError, ValueError, TypeError):
            pass
        return result

    def save(self):
        try:
            temporary = SETTINGS.with_suffix('.tmp')
            temporary.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(SETTINGS)
        except OSError:
            pass


def label(text='', kind=None):
    widget = QLabel(text)
    if kind:
        widget.setObjectName(kind)
    return widget


def button(text, callback, kind=None):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if kind:
        widget.setObjectName(kind)
    widget.clicked.connect(callback)
    return widget


class DragHeader(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()


STYLE = '''
QWidget { font-family: "Microsoft YaHei UI"; font-size: 13px; color: #242735; }
QFrame#Shell { background: #F7F8FC; border: 1px solid #E4E5ED; border-radius: 18px; }
QFrame#Sidebar { background: #1C1D2B; border-radius: 14px; }
QLabel#Brand { color: #F4EFFF; font-size: 22px; font-weight: 700; }
QLabel#Wordmark { color: #222435; font-size: 17px; font-weight: 700; }
QLabel#Overline { color: #8B84A5; font-family: "Segoe UI"; font-size: 10px; font-weight: 700; }
QLabel#Heading { color: #232536; font-size: 25px; font-weight: 700; }
QLabel#Subtle { color: #858698; font-size: 12px; }
QLabel#Section { color: #272A3D; font-size: 15px; font-weight: 700; }
QLabel#Connection { background: #EEEBFA; color: #76629E; border-radius: 12px; padding: 6px 12px; font-size: 11px; }
QLabel#Footer { color: #9899AA; font-size: 11px; }
QFrame#Card { background: white; border: 1px solid #EBEBF3; border-radius: 16px; }
QPushButton { background: #FFFFFF; border: 1px solid #E5E4EF; border-radius: 9px; padding: 8px 13px; }
QPushButton:hover { background: #F2EFFB; border-color: #C5BAE5; }
QPushButton:pressed { background: #E6DEF8; }
QPushButton#Primary { background: #7963BA; color: white; border: 0; font-weight: 600; padding: 11px 18px; }
QPushButton#Primary:hover { background: #6954A8; }
QPushButton#Nav { color: #9292A8; background: transparent; border: 0; padding: 16px 4px; font-size: 11px; }
QPushButton#Nav:checked { color: #E3D7FF; background: #343047; border-radius: 10px; }
QPushButton#WindowButton { border: 0; background: transparent; color: #9897AB; padding: 3px 8px; font-size: 17px; }
QPushButton#WindowButton:hover { background: #E9E7F1; color: #333342; }
QPushButton#Chip { background: #F1EEF9; color: #7963BA; border: 0; padding: 5px 9px; font-size: 11px; }
QLineEdit, QComboBox, QFontComboBox { background: #F7F7FB; border: 1px solid #E8E7F1; border-radius: 7px; padding: 7px 9px; selection-background-color: #BBA8E6; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #A38BD2; }
QComboBox::drop-down { border: 0; width: 22px; }
QComboBox QAbstractItemView { background: white; selection-background-color: #E9E1F8; }
QCheckBox { spacing: 9px; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #D3D0E1; border-radius: 5px; background: #F9F8FC; }
QCheckBox::indicator:checked { background: #8870C5; border-color: #8870C5; image: none; }
QCheckBox::indicator:checked:hover { background: #725BAD; }
QSlider::groove:horizontal { height: 5px; border-radius: 2px; background: #ECE9F3; }
QSlider::sub-page:horizontal { background: #A18BCF; border-radius: 2px; }
QSlider::handle:horizontal { width: 14px; margin: -5px 0; border-radius: 7px; background: #8067BA; }
QSlider::handle:horizontal:hover { background: #664A9F; }
QListWidget { background: white; border: 1px solid #E8E7F1; border-radius: 10px; outline: none; padding: 5px; }
QListWidget::item { padding: 10px 8px; border-radius: 6px; }
QListWidget::item:selected { background: #EEE8FA; color: #7358A7; }
QListWidget::item:hover { background: #F5F2FB; }
QTextBrowser { background: white; border: 1px solid #E8E7F1; border-radius: 10px; padding: 10px; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { width: 5px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #D6D1E3; border-radius: 2px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QMenu { background: white; border: 1px solid #E4DFEE; padding: 5px; }
QMenu::item { padding: 8px 18px; }
QMenu::item:selected { background: #EEE8FA; }
QTabWidget::pane { border: 0; background: transparent; }
QTabBar::tab { background: #EFEAF7; color: #9283AB; padding: 9px 12px; border: 0; margin-right: 3px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
QTabBar::tab:selected { color: #6C529C; background: white; font-weight: 600; }
QTabBar::tab:hover { color: #6C529C; }
'''


class Studio(QWidget):
    def __init__(self):
        super().__init__()
        self.appearance = Appearance.load()
        self.setWindowTitle('浮词 · 桌面歌词设置')
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(STYLE)
        area = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1120, area.width() - 70), min(730, area.height() - 80))
        self.setMinimumSize(920, 600)
        self.move(area.center() - self.rect().center())
        self.lines, self.files = [], []
        self.current_file = None
        self.identity = None
        self.offset = 0
        self.index = -1
        self.follow = True
        self.folder = discover_folder()
        self.next_scan = 0
        self.last_diagnostic = 0
        self.last_list_index = -2
        self.player_clock = PlaybackClock()
        self.provider = LyricProvider()
        self.lyric_source = ''
        self.next_status_update = 0
        self.overlay = LyricCanvas(self.appearance)
        self.overlay.open_settings.connect(self.restore)
        self.overlay.moved.connect(self.save_position)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.appearance.save)
        self.build()
        self.setup_tray()
        self.refresh_files()
        self.overlay.refresh_appearance()
        if self.appearance.anchor != 'custom' or self.appearance.x is None or self.appearance.y is None:
            self.center_overlay()
        else:
            self.overlay.move(self.appearance.x, self.appearance.y)
            self.keep_overlay_on_screen()
        self.overlay.setVisible(self.appearance.visible)
        self.reader = PlaybackSource()
        if hasattr(self.reader,'set_player'):
            self.reader.set_player(self.appearance.player)
        self.set_content('等待'+PLAYERS[self.appearance.player]+'播放…','')
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.start(round(1000 / self.appearance.fps))
        self.quitting = False

    def build(self):
        outside = QVBoxLayout(self)
        outside.setContentsMargins(0, 0, 0, 0)
        shell = QFrame(objectName='Shell')
        outside.addWidget(shell)
        root = QHBoxLayout(shell)
        root.setContentsMargins(10, 10, 24, 14)
        root.setSpacing(24)
        sidebar = QFrame(objectName='Sidebar')
        sidebar.setFixedWidth(76)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(9, 22, 9, 18)
        nav.addWidget(label('浮', 'Brand'), alignment=Qt.AlignmentFlag.AlignHCenter)
        nav.addSpacing(32)
        self.nav_buttons = []
        for text, index in [('◈\n外观', 0), ('♫\n曲库', 1), ('ⓘ\n关于', 2)]:
            item = button(text, lambda checked=False, i=index: self.set_page(i), 'Nav')
            item.setCheckable(True)
            self.nav_buttons.append(item)
            nav.addWidget(item)
        nav.addStretch()
        nav.addWidget(label('FLOAT', 'Overline'), alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(sidebar)
        workspace = QVBoxLayout()
        workspace.setSpacing(16)
        root.addLayout(workspace, 1)
        header = DragHeader()
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(0, 6, 0, 0)
        header_row.addWidget(label('浮词', 'Wordmark'))
        header_row.addWidget(label('  /  DESKTOP LYRICS', 'Overline'))
        header_row.addStretch()
        self.player_status_labels = {}
        for key,name in PLAYERS.items():
            chip=label('○ '+name, 'Connection')
            chip.setToolTip('正在检测是否打开及媒体连接状态')
            self.player_status_labels[key]=chip
            header_row.addWidget(chip)
        self.connection = self.player_status_labels[self.appearance.player]
        header_row.addSpacing(8)
        minimise = button('−', self.showMinimized, 'WindowButton')
        minimise.setToolTip('最小化设置窗口')
        header_row.addWidget(minimise)
        close = button('×', self.fold, 'WindowButton')
        close.setToolTip('收起设置，桌面歌词继续显示；可从托盘恢复')
        header_row.addWidget(close)
        workspace.addWidget(header)
        sources = QHBoxLayout()
        sources.setSpacing(18)
        sources.addWidget(label('歌词来源', 'Subtle'))
        self.source_group=QButtonGroup(self)
        self.source_radios={}
        for key,name in PLAYERS.items():
            radio=QRadioButton(name)
            radio.setChecked(key==self.appearance.player)
            radio.toggled.connect(lambda checked,player=key:self.select_player(player) if checked else None)
            self.source_group.addButton(radio)
            self.source_radios[key]=radio
            sources.addWidget(radio)
        sources.addStretch()
        workspace.addLayout(sources)
        heading = QHBoxLayout()
        title_group = QVBoxLayout()
        title_group.setSpacing(3)
        self.page_title = label('桌面，只留歌词。', 'Heading')
        self.page_subtitle = label('无边框 · 透明背景 · 随音乐同步', 'Subtle')
        title_group.addWidget(self.page_title)
        title_group.addWidget(self.page_subtitle)
        heading.addLayout(title_group)
        heading.addStretch()
        self.follow_check = QCheckBox('跟随所选播放器')
        self.follow_check.setChecked(True)
        self.follow_check.toggled.connect(self.set_follow)
        heading.addWidget(self.follow_check)
        workspace.addLayout(heading)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.appearance_page())
        self.pages.addWidget(self.library_page())
        self.pages.addWidget(build_about_page(self))
        workspace.addWidget(self.pages, 1)
        footer = QHBoxLayout()
        self.footer = label('等待音乐播放', 'Footer')
        footer.addWidget(self.footer)
        footer.addStretch()
        footer.addWidget(label('作者 Kerwin · 外观设置自动保存', 'Footer'))
        workspace.addLayout(footer)
        self.set_page(0)

    def appearance_page(self):
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(20)
        left = QVBoxLayout()
        left.setSpacing(14)
        self.preview = LyricCanvas(self.appearance, preview=True)
        left.addWidget(self.preview, 1)
        playing = QFrame(objectName='Card')
        track_box = QVBoxLayout(playing)
        track_box.setContentsMargins(20, 16, 20, 16)
        tiny = QHBoxLayout()
        tiny.addWidget(label('NOW PLAYING', 'Overline'))
        tiny.addStretch()
        self.clock = label('— : —', 'Subtle')
        tiny.addWidget(self.clock)
        track_box.addLayout(tiny)
        self.track_title = label('等待'+PLAYERS[self.appearance.player]+'播放', 'Section')
        self.track_title.setWordWrap(True)
        self.track_artist = label('歌词会自动跟随当前歌曲', 'Subtle')
        self.track_artist.setWordWrap(True)
        track_box.addWidget(self.track_title)
        track_box.addWidget(self.track_artist)
        self.sync_detail=label('歌曲等待 · 进度等待 · 歌词等待','Subtle')
        self.sync_detail.setAccessibleName('同步状态')
        self.sync_detail.setWordWrap(True)
        track_box.addWidget(self.sync_detail)
        left.addWidget(playing)
        actions = QHBoxLayout()
        actions.addWidget(button('只留桌面歌词  ↗', self.fold, 'Primary'), 1)
        actions.addWidget(button('位置复原', self.center_overlay))
        left.addLayout(actions)
        left.addWidget(label('拖动桌面歌词可移动 · 双击可打开设置', 'Subtle'))
        row.addLayout(left, 1)
        row.addWidget(build_controls(self))
        return page

    def add_slider(self, layout, title, key, minimum, maximum, suffix):
        row = QHBoxLayout()
        row.addWidget(label(title))
        row.addStretch()
        value = label(str(getattr(self.appearance, key)) + suffix, 'Subtle')
        row.addWidget(value)
        layout.addLayout(row)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(getattr(self.appearance, key))
        slider.setAccessibleName(title)
        slider.valueChanged.connect(lambda number: (value.setText(str(number) + suffix), self.change(key, number)))
        layout.addWidget(slider)
        if hasattr(self, 'control_widgets'):
            self.control_widgets[key] = slider
        return slider

    def library_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        tools = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索歌名或歌手')
        self.search.textChanged.connect(self.populate_library)
        tools.addWidget(self.search, 1)
        tools.addWidget(button('选择目录', self.pick_folder))
        tools.addWidget(button('打开歌词', self.pick_file))
        tools.addWidget(button('刷新', self.refresh_files))
        layout.addLayout(tools)
        columns = QHBoxLayout()
        self.library = QListWidget()
        self.library.setMinimumWidth(250)
        self.library.itemClicked.connect(self.manual_file)
        columns.addWidget(self.library, 1)
        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(False)
        columns.addWidget(self.transcript, 2)
        layout.addLayout(columns, 1)
        self.library_info = label(str(self.folder), 'Subtle')
        self.library_info.setWordWrap(True)
        layout.addWidget(self.library_info)
        return page

    def set_page(self, index):
        if not hasattr(self, 'pages'):
            return
        self.pages.setCurrentIndex(index)
        for i, nav in enumerate(self.nav_buttons):
            nav.setChecked(i == index)
        self.page_title.setText(['桌面，只留歌词。','你的本地曲库','关于浮词'][index])
        self.page_subtitle.setText(['无边框 · 透明背景 · 随音乐同步','自动匹配酷狗缓存，也可以手动打开歌词','创作、联系与许可'][index])

    def update_swatches(self):
        for swatch, color in self.swatches:
            selected = color.casefold() == self.appearance.color.casefold()
            border = '3px solid #8067BA' if selected else '2px solid #E1DFEB'
            swatch.setStyleSheet(f'QPushButton {{ background: {color}; border: {border}; border-radius: 17px; padding: 0; }}')

    def change(self, key, value):
        previous_mode = self.appearance.mode
        ink_anchor = None
        if key in ('perspective_enabled','perspective_angle','perspective_direction','roll') and self.appearance.anchor == 'custom' and self.overlay.lines:
            bounds = self.overlay.visible_ink_bounds()
            if not bounds.isEmpty():
                ink_anchor = QPointF(self.overlay.x() + bounds.left(), self.overlay.y() + bounds.top())
        if key == 'mode' and value != previous_mode:
            self.remember_layout()
        setattr(self.appearance, key, value)
        if key == 'mode' and value != previous_mode:
            profile = self.appearance.positions.get(value, {})
            self.appearance.anchor = profile.get('anchor', 'center' if value == 'duet' else 'left')
            self.appearance.region_vertical = profile.get('region_vertical', 'bottom' if value == 'duet' else 'center')
            self.appearance.x, self.appearance.y = profile.get('x'), profile.get('y')
        for name, control in getattr(self, 'control_widgets', {}).items():
            if isinstance(control, QComboBox):
                index = control.findData(getattr(self.appearance, name))
                if index >= 0 and index != control.currentIndex():
                    control.blockSignals(True)
                    control.setCurrentIndex(index)
                    control.blockSignals(False)
        if key in ('topmost', 'locked'):
            self.overlay.apply_flags()
        self.overlay.setVisible(self.appearance.visible)
        if key == 'color':
            self.color_edit.setText(value.upper())
            self.update_swatches()
        self.preview.refresh_appearance()
        self.overlay.refresh_appearance()
        if ink_anchor is not None:
            bounds = self.overlay.visible_ink_bounds()
            self.overlay.move(round(ink_anchor.x() - bounds.left()), round(ink_anchor.y() - bounds.top()))
            self.keep_overlay_on_screen()
            self.appearance.x, self.appearance.y = self.overlay.x(), self.overlay.y()
        elif key == 'mode' and self.appearance.anchor == 'custom' and self.appearance.x is not None and self.appearance.y is not None:
            self.overlay.move(self.appearance.x, self.appearance.y)
        elif key in ('mode','anchor','region_vertical','region_width','region_height') and self.appearance.anchor != 'custom':
            self.center_overlay()
        elif key in ('region_width','region_height','background_opacity'):
            self.keep_overlay_on_screen()
            self.appearance.x, self.appearance.y = self.overlay.x(), self.overlay.y()
        if key == 'fps' and hasattr(self, 'timer'):
            self.timer.setInterval(round(1000 / self.appearance.fps))
        if 'perspective_enabled' in self.checks:
            self.checks['perspective_enabled'].setEnabled(self.appearance.mode == 'scroll')
        self.save_timer.start(350)
        if hasattr(self, 'tray_visible'):
            self.tray_visible.setChecked(self.appearance.visible)
            self.tray_lock.setChecked(self.appearance.locked)

    def edit_color(self):
        value = self.color_edit.text().strip()
        if len(value) == 7 and value.startswith('#') and QColor(value).isValid():
            self.change('color', QColor(value).name().upper())
        else:
            self.color_edit.setText(self.appearance.color)

    def preview_motion(self):
        # Replay only the visual entrance; preserve player position and lyrics.
        now = time.monotonic()
        for canvas in (self.preview, self.overlay):
            canvas.focus_from = {}
            canvas.focus_start = now
            canvas.update()

    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.appearance.color), self, '选择歌词颜色')
        if color.isValid():
            self.change('color', color.name().upper())

    def center_overlay(self):
        screen = self.overlay.screen().availableGeometry()
        a = self.appearance
        x = screen.left() + 28 if a.anchor == 'left' else screen.right() - self.overlay.width() - 28 if a.anchor == 'right' else screen.left() + (screen.width() - self.overlay.width()) // 2
        y = screen.top() + 28 if a.region_vertical == 'top' else screen.bottom() - self.overlay.height() - 38 if a.region_vertical == 'bottom' else screen.top() + (screen.height() - self.overlay.height()) // 2
        self.overlay.move(x, y)
        self.appearance.x, self.appearance.y = self.overlay.x(), self.overlay.y()
        self.save_timer.start(350)

    def keep_overlay_on_screen(self):
        if not self.overlay.lines:
            return
        area = self.overlay.screen().availableGeometry()
        ink = self.overlay.visible_ink_bounds()
        if not ink.isEmpty():
            from lyric_renderer import clamp_ink_position
            self.overlay.move(clamp_ink_position(self.overlay.pos(), ink, area))

    def remember_layout(self):
        a = self.appearance
        a.positions[a.mode] = dict(x=self.overlay.x(), y=self.overlay.y(),
                                  anchor=a.anchor, region_vertical=a.region_vertical)

    def save_position(self):
        self.keep_overlay_on_screen()
        self.appearance.x, self.appearance.y = self.overlay.x(), self.overlay.y()
        self.appearance.anchor = 'custom'
        self.remember_layout()
        control = getattr(self, 'control_widgets', {}).get('anchor')
        if control:
            control.blockSignals(True)
            control.setCurrentIndex(control.findData('custom'))
            control.blockSignals(False)
        self.save_timer.start(350)

    def setup_tray(self):
        icon_image = QPixmap(32, 32)
        icon_image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(icon_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#8067BA'))
        painter.drawRoundedRect(QRectF(0, 0, 32, 32), 9, 9)
        painter.setPen(QColor('white'))
        painter.setFont(QFont('Microsoft YaHei UI', 16, QFont.Weight.Bold))
        painter.drawText(icon_image.rect(), Qt.AlignmentFlag.AlignCenter, '浮')
        painter.end()
        icon = QIcon(str(APP_ICON)) if APP_ICON.is_file() else QIcon(icon_image)
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip('浮词 · 双击打开设置')
        menu = QMenu()
        menu.addAction('打开浮词设置', self.restore)
        self.tray_visible = menu.addAction('显示桌面歌词')
        self.tray_visible.setCheckable(True)
        self.tray_visible.setChecked(self.appearance.visible)
        self.tray_visible.triggered.connect(lambda checked: self.checks['visible'].setChecked(checked))
        self.tray_lock = menu.addAction('鼠标穿透')
        self.tray_lock.setCheckable(True)
        self.tray_lock.setChecked(self.appearance.locked)
        self.tray_lock.triggered.connect(lambda checked: self.checks['locked'].setChecked(checked))
        menu.addSeparator()
        menu.addAction('退出浮词', self.quit)
        self.tray.setContextMenu(menu)
        self.tray_menu = menu
        self.tray.activated.connect(lambda reason: self.restore() if reason in
            (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger) else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def fold(self):
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
        else:
            self.showMinimized()

    def restore(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def refresh_files(self):
        try:
            self.files = scan(self.folder)
            self.populate_library()
            self.library_info.setText(f'{len(self.files)} 份本地歌词  ·  {self.folder}')
        except (OSError, ValueError) as exc:
            self.footer.setText(str(exc))

    def populate_library(self):
        self.library.clear()
        needle = self.search.text().strip().casefold()
        for path in self.files:
            if needle not in short_name(path).casefold():
                continue
            item = QListWidgetItem(short_name(path))
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(short_name(path))
            self.library.addItem(item)

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择歌词目录', str(self.folder))
        if folder:
            self.folder = Path(folder)
            self.current_file = None
            self.refresh_files()
            self.next_scan = 0

    def pick_file(self):
        path, _ = QFileDialog.getOpenFileName(self, '打开歌词', str(self.folder), '歌词文件 (*.krc *.lrc)')
        if path:
            self.follow_check.setChecked(False)
            if self.load_file(Path(path)):
                self.display_line(0)

    def manual_file(self, item):
        self.follow_check.setChecked(False)
        if self.load_file(Path(item.data(Qt.ItemDataRole.UserRole))):
            self.display_line(0)

    def set_follow(self, checked):
        self.follow = checked
        self.identity = None
        self.current_file = None
        self.next_scan = 0
        if not checked:
            self.connection.setText('●  手动查看')
            self.footer.setText('正在手动预览；开启“跟随所选播放器”可恢复同步')

    def select_player(self, player):
        if player==self.appearance.player:return
        self.appearance.player=player
        if hasattr(self.reader,'set_player'):self.reader.set_player(player)
        self.connection=self.player_status_labels[player]
        self.identity=None;self.current_file=None;self.lines=[];self.index=-2;self.offset=0
        self.player_clock=PlaybackClock();self.next_scan=0;self.lyric_source=''
        self.track_title.setText('等待'+PLAYERS[player]+'播放')
        self.track_artist.setText('已切换歌词来源')
        self.transcript.clear();self.clock.setText('— : —')
        self.set_content('等待'+PLAYERS[player]+'播放…','')
        self.follow_check.setChecked(True)
        self.save_timer.start(350)

    def update_player_statuses(self,now):
        if now<self.next_status_update or not hasattr(self.reader,'statuses'):return
        self.next_status_update=now+1
        rows=self.reader.statuses()
        selected,stamp=self.reader.snapshot()
        for key,name in PLAYERS.items():
            row=rows.get(key,{})
            connected=(key==self.appearance.player and selected and selected.get('ok') and selected.get('progress_ok',True) and now-stamp<4) or (row.get('ok') and row.get('timeline_valid'))
            state='已连接' if connected else '已打开' if row.get('running') else '未打开'
            self.player_status_labels[key].setText(('● ' if row.get('running') else '○ ')+name+' · '+state)
            self.player_status_labels[key].setToolTip('已连接：可读取歌曲和进度；已打开：检测到进程，等待播放信息。')

    def load_file(self, path):
        try:
            meta, lines = parse_lyrics(decode_file(path), path.suffix)
            self.lines, self.current_file = lines, path
            self.offset = int(meta.get('offset', 0))
            self.index = -2
            self.last_list_index = -2
            text = short_name(path)
            artist, sep, song = text.partition(' - ')
            self.track_title.setText(meta.get('ti') or song or text)
            self.track_artist.setText(meta.get('ar') or artist if sep else meta.get('ar', '本地歌词'))
            self.transcript.setPlainText('\n'.join(line.text for line in self.lines))
            return True
        except Exception as exc:
            self.footer.setText(f'歌词暂时无法读取：{exc}')
            return False

    def display_line(self, index):
        if not self.lines or index < 0:
            self.set_content('等待第一句…', '')
            return
        self.render_position(index, self.lines[index].start_ms)
        if index != self.last_list_index:
            cursor = self.transcript.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.NextBlock, cursor.MoveMode.MoveAnchor, index)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            self.transcript.setTextCursor(cursor)
            self.transcript.ensureCursorVisible()
            self.last_list_index = index

    def render_position(self, index, position, snap=False):
        previous_size = self.overlay.size()
        for canvas in (self.overlay, self.preview):
            canvas.set_sequence(self.lines, index, position, self.track_title.text(), snap)
        if self.overlay.size() != previous_size:
            if self.appearance.anchor != 'custom':
                self.center_overlay()
            else:
                self.keep_overlay_on_screen()

    def set_content(self, current, upcoming):
        track = self.track_title.text()
        changed = (current, upcoming) != (self.overlay.current, self.overlay.upcoming)
        self.overlay.set_content(current, upcoming, track)
        self.preview.set_content(current, upcoming, track)
        if changed:
            self.overlay.refresh_appearance()
            self.keep_overlay_on_screen()

    def tick(self):
        try:
            self.update_playback()
        except Exception as exc:
            self.footer.setText(f'正在恢复同步：{exc}')

    def update_playback(self):
        now = time.monotonic()
        self.update_player_statuses(now)
        if not self.follow:
            return
        data, received = self.reader.snapshot()
        now = time.monotonic()
        if not data or not data.get('ok') or now - received > 4:
            self.footer.setText((data or {}).get('error', '正在连接'+PLAYERS[self.appearance.player]))
            if data and now - received > 4:
                self.footer.setText('播放状态更新超时，可尝试展开所选播放器主窗口')
            if self.lines:
                self.lines=[];self.current_file=None;self.identity=None
                self.set_content('等待'+PLAYERS[self.appearance.player]+'播放…','')
            self.sync_detail.setText('歌曲等待 · 进度等待 · 歌词等待')
            self.write_diagnostic(data or {},received)
            return
        progress_ok=data.get('progress_ok',True)
        if progress_ok:self.player_clock.accept(data, received)
        identity = data['identity']
        if identity != self.identity:
            self.identity = identity
            self.current_file = None
            self.lines = []
            self.index = -2
            self.offset = 0
            self.lyric_source = ''
            artist, sep, song = identity.partition(' - ')
            self.track_title.setText(song or identity)
            self.track_artist.setText(artist if sep else '')
            self.transcript.clear()
            self.next_scan = 0
            self.set_content('正在读取歌词…', '')
        if self.appearance.player!='kugou' and self.current_file is None:
            self.provider.request(self.appearance.player,dict(data))
            result=self.provider.snapshot()
            if result and result.get('key')==(self.appearance.player,identity):
                if result.get('ok'):
                    self.lines=result['lines'];self.lyric_source=result['source'];self.offset=0;self.index=-2
                    self.current_file=Path('player-lyrics')/self.appearance.player
                    self.transcript.setPlainText('\n'.join(line.text for line in self.lines))
                else:
                    self.set_content('暂未取得匹配歌词','')
                    self.footer.setText(result['error'])
            else:self.set_content('正在获取匹配歌词…','')
        if self.appearance.player=='kugou' and self.current_file is None and now >= self.next_scan:
            self.next_scan = now + 1.5
            self.refresh_files()
            path = match_file(self.files, identity)
            if path:
                self.load_file(path)
            else:
                self.set_content('暂无本地歌词', '')
        position, duration = int(self.player_clock.position(now)) if progress_ok else 0, max(0,round(data.get('duration_ms',0)))
        state = '已暂停' if data['state'] == 'paused' else '播放中' if data['state'] == 'playing' else '已连接'
        self.clock.setText(f'{position // 60000:02d}:{position // 1000 % 60:02d}  /  {duration // 60000:02d}:{duration // 1000 % 60:02d}' if progress_ok else '— : —  /  '+(f'{duration // 60000:02d}:{duration // 1000 % 60:02d}' if duration else '— : —'))
        timing = '逐字／词时间' if any(line.words for line in self.lines) else '整句匀速估算'
        if self.current_file:
            clock_source='界面进度条估算' if data.get('precision')=='fraction' else '整秒进度插值' if data.get('precision')=='second' else '系统媒体时间轴'
            self.footer.setText(f'{state} · {self.lyric_source or "酷狗本地缓存"} · {timing} · {clock_source}' if progress_ok else '歌词已就绪 · '+data.get('error','等待播放器进度'))
        elif self.appearance.player=='kugou':self.footer.setText(f'{state} · 等待酷狗生成本地歌词缓存')
        self.sync_detail.setText('歌曲已识别 · '+('进度正常' if progress_ok else '进度等待')+' · '+('歌词已就绪' if self.current_file else '歌词获取中'))
        index = bisect_right([line.start_ms for line in self.lines], position + self.offset) - 1 if progress_ok else -1
        if index != self.index:
            self.index = index
            if self.current_file:
                self.display_line(index)
        if self.current_file:
            self.render_position(index, position, self.player_clock.seek)
        self.write_diagnostic(data,received,index,position,timing)

    def write_diagnostic(self,data,received,index=-1,position=0,timing=''):
        now=time.monotonic()
        if now - self.last_diagnostic > .8:
            self.last_diagnostic = now
            result=self.provider.snapshot()
            lyric_error=(result or {}).get('error','') if (result or {}).get('key')==(self.appearance.player,data.get('identity')) else ''
            debug = dict(data, player=self.appearance.player,lyric_source=self.lyric_source, matched_file=str(self.current_file) if self.current_file else None,
                         highlighted_line=index, overlay_visible=self.appearance.visible,
                         color=self.appearance.color, opacity=self.appearance.opacity,
                         overlay_text=self.overlay.current, estimated_position_ms=position,
                         mode=self.appearance.mode, line_count=self.appearance.line_count,
                         timing_source=timing,diagnosed_unix_ms=round(time.time()*1000),
                         stages=dict(song=bool(data.get('ok') and now-received<=4),progress=bool(data.get('ok') and data.get('progress_ok',True) and now-received<=4),lyrics=bool(self.current_file)),
                         lyric_error=lyric_error,reader_age_ms=round(max(0,now-received)*1000))
            try:
                temp = BASE / 'sync_state.tmp'
                temp.write_text(json.dumps(debug, ensure_ascii=False, indent=2), encoding='utf-8')
                temp.replace(BASE / 'sync_state.json')
                signature=(self.appearance.player,data.get('identity'),str(debug['stages']),data.get('error'),lyric_error)
                if signature!=getattr(self,'diagnostic_signature',None):
                    self.diagnostic_signature=signature
                    event=BASE/'sync_events.jsonl'
                    if event.is_file() and event.stat().st_size>2*1024*1024:event.replace(BASE/'sync_events.previous.jsonl')
                    with event.open('a',encoding='utf-8') as stream:stream.write(json.dumps(debug,ensure_ascii=False)+'\n')
            except OSError:
                pass

    def closeEvent(self, event):
        if self.quitting:
            event.accept()
        else:
            self.fold()
            event.ignore()

    def quit(self):
        if self.quitting:
            return
        self.quitting = True
        self.timer.stop()
        self.reader.close()
        self.remember_layout()
        self.appearance.save()
        self.tray.hide()
        self.overlay.close()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName('浮词')
    app.setWindowIcon(QIcon(str(APP_ICON)))
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('FloatingLyrics.Desktop.1')
    app.setFont(QFont('Microsoft YaHei UI', 10))
    # Relaunching the shortcut restores the existing studio, including from the tray.
    endpoint = 'floating-lyrics-' + hashlib.sha256(str(BASE).casefold().encode()).hexdigest()[:16]
    client = QLocalSocket()
    client.connectToServer(endpoint)
    if client.waitForConnected(400):
        client.disconnectFromServer()
        return
    server = QLocalServer(app)
    if not server.listen(endpoint):
        raise RuntimeError('无法创建浮词的本地窗口唤醒通道')
    studio = Studio()
    def restore_existing():
        socket = server.nextPendingConnection()
        if socket:
            studio.restore()
            socket.disconnectFromServer()
            socket.deleteLater()
    server.newConnection.connect(restore_existing)
    app.aboutToQuit.connect(studio.quit)
    studio.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
