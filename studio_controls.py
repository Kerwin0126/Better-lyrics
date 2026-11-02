# Author: Kerwin
"""Grouped appearance controls for the lyric studio."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (QTabWidget, QScrollArea, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QComboBox, QFontComboBox, QLineEdit, QPushButton, QColorDialog)


def text(value, kind=None):
    widget = QLabel(value)
    widget.setWordWrap(True)
    if kind:
        widget.setObjectName(kind)
    return widget


def action(title, callback):
    result = QPushButton(title)
    result.setCursor(Qt.CursorShape.PointingHandCursor)
    result.clicked.connect(callback)
    return result


def build_controls(studio):
    tabs = QTabWidget()
    tabs.setFixedWidth(320)
    studio.control_widgets = {}
    studio.checks = {}
    a = studio.appearance

    def page(title):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        card = QFrame(objectName='Card')
        form = QVBoxLayout(card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)
        scroll.setWidget(card)
        tabs.addTab(scroll, title)
        return form

    def combo(form, title, key, options):
        form.addWidget(text(title, 'Section'))
        widget = QComboBox()
        widget.setMinimumContentsLength(12)
        widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        widget.setMinimumWidth(0)
        widget.setAccessibleName(title)
        for caption, value in options:
            widget.addItem(caption, value)
        widget.setCurrentIndex(widget.findData(getattr(a, key)))
        widget.currentIndexChanged.connect(lambda index: studio.change(key, widget.itemData(index)))
        studio.control_widgets[key] = widget
        form.addWidget(widget)

    def check(form, title, key):
        widget = QCheckBox(title)
        widget.setChecked(getattr(a, key))
        widget.toggled.connect(lambda checked: studio.change(key, checked))
        studio.checks[key] = widget
        form.addWidget(widget)

    style = page('样式')
    combo(style, '歌词布局', 'mode', [('双行悬浮 · 当前句与下一句','duet'), ('侧边列表 · 多行滚动','scroll')])
    check(style, '显示桌面歌词', 'visible')
    check(style, '始终置顶', 'topmost')
    check(style, '鼠标穿透', 'locked')
    style.addWidget(text('关闭穿透后可拖动歌词；双击歌词可打开设置。', 'Subtle'))
    style.addWidget(text('字体', 'Section'))
    studio.font_combo = QFontComboBox()
    studio.font_combo.setMinimumContentsLength(10)
    studio.font_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    studio.font_combo.setMinimumWidth(0)
    studio.font_combo.setCurrentFont(QFont(a.font))
    studio.font_combo.currentFontChanged.connect(lambda font: studio.change('font', font.family()))
    style.addWidget(studio.font_combo)
    studio.add_slider(style, '基础字号', 'size', 20, 68, ' pt')
    studio.add_slider(style, '文字不透明度', 'opacity', 20, 100, '%')
    check(style, '加粗文字', 'bold')
    check(style, '文字描边', 'outline')
    check(style, '双行模式显示下一句', 'next_line')
    combo(style, '当前句动效', 'motion', [('轻浮聚焦','float'), ('柔和放大','focus'), ('关闭动效','none')])
    studio.add_slider(style, '放大动效强度', 'motion_strength', 0, 100, '%')
    studio.add_slider(style, '动效时长', 'motion_duration', 120, 700, ' ms')
    style.addWidget(action('预览一次放大动效', studio.preview_motion))
    check(style, '当前字／词波浪浮动', 'word_wave')
    studio.add_slider(style, '波浪幅度', 'wave_strength', 0, 100, '%')
    studio.add_slider(style, '波浪速度', 'wave_speed', 50, 200, '%')
    style.addWidget(text('放大强度控制进入时的缩放；稳定后的字号仍由“排版 → 当前句放大”决定。波浪跟随字词时间，可与放大叠加。', 'Subtle'))
    combo(style, '刷新率', 'fps', [('流畅 · 60 帧目标',60), ('省电 · 30 帧目标',30)])
    style.addStretch()

    layout = page('排版')
    studio.add_slider(layout, '显示行数', 'line_count', 1, 24, ' 行')
    studio.add_slider(layout, '当前句放大', 'active_scale', 100, 180, '%')
    studio.add_slider(layout, '行间距', 'line_spacing', 110, 220, '%')
    combo(layout, '文字横向对齐', 'align', [('左对齐','left'), ('居中','center'), ('右对齐','right')])
    combo(layout, '内容竖向对齐', 'vertical', [('顶部','top'), ('居中','center'), ('底部','bottom')])
    combo(layout, '区域在屏幕的位置', 'anchor', [('屏幕左侧','left'), ('屏幕居中','center'), ('屏幕右侧','right'), ('自由拖动','custom')])
    combo(layout, '区域竖向位置', 'region_vertical', [('顶部','top'), ('居中','center'), ('底部','bottom')])
    studio.add_slider(layout, '区域宽度', 'region_width', 320, 1600, ' px')
    studio.add_slider(layout, '区域高度', 'region_height', 240, 1400, ' px')
    layout.addWidget(text('列表中每句占一行，长句会自动缩小。区域太小时会整体缩放，以容纳设定行数。', 'Subtle'))
    layout.addStretch()

    colors = page('配色')
    colors.addWidget(text('已唱过 / 当前强调色', 'Section'))
    swatches = QHBoxLayout()
    studio.swatches = []
    for title, value in [('月光','#F4F0FF'), ('薄荷','#8FF0CE'), ('落日','#FFBE91'), ('雾紫','#C4ACFF'), ('墨色','#292D40')]:
        swatch = action('', lambda checked=False, color=value: studio.change('color', color))
        swatch.setFixedSize(32, 32)
        swatch.setToolTip(title + ' ' + value)
        swatch.setAccessibleName(title + '歌词颜色')
        studio.swatches.append((swatch, value))
        swatches.addWidget(swatch)
    swatches.addStretch()
    colors.addLayout(swatches)
    row = QHBoxLayout()
    studio.color_edit = QLineEdit(a.color)
    studio.color_edit.setMaxLength(7)
    studio.color_edit.setAccessibleName('已唱过颜色')
    studio.color_edit.editingFinished.connect(studio.edit_color)
    row.addWidget(studio.color_edit, 1)
    row.addWidget(action('自定义', studio.pick_color))
    colors.addLayout(row)

    def extra_color(title, key, form=colors):
        form.addWidget(text(title, 'Section'))
        row = QHBoxLayout()
        editor = QLineEdit(getattr(a, key))
        editor.setMaxLength(7)
        editor.setAccessibleName(title)
        def commit():
            value = editor.text().strip()
            if len(value) == 7 and value.startswith('#') and QColor(value).isValid():
                studio.change(key, QColor(value).name().upper())
            else:
                editor.setText(getattr(a, key))
        def choose():
            color = QColorDialog.getColor(QColor(getattr(a,key)), studio, title)
            if color.isValid():
                studio.change(key, color.name().upper())
                editor.setText(color.name().upper())
        editor.editingFinished.connect(commit)
        row.addWidget(editor, 1)
        row.addWidget(action('选择', choose))
        form.addLayout(row)
    extra_color('还没唱到', 'pending_color')
    extra_color('其他歌词行', 'context_color')
    studio.add_slider(colors, '其他行不透明度', 'inactive_opacity', 10, 100, '%')
    check(colors, '逐字 / 词变色', 'karaoke')
    check(colors, '当前字／词轻微发光', 'word_glow')
    colors.addWidget(text('KRC 使用字／词时间；LRC 按整句时长估算。播放器进度为整秒时，动画会插值平滑，实际时刻仍有误差。', 'Subtle'))
    colors.addStretch()

    background = page('背景')
    background.addWidget(text('一层安静的磨砂玻璃', 'Section'))
    background.addWidget(text('默认 0% 完全透明；调高后，为整个歌词区域铺上圆角半透明背景。双行、侧边和 3D 布局都适用。', 'Subtle'))
    studio.add_slider(background, '背景不透明度', 'background_opacity', 0, 100, '%')
    check(background, '磨砂模糊', 'background_blur')
    studio.add_slider(background, '圆角大小', 'background_radius', 0, 80, ' px')
    extra_color('背景颜色', 'background_color', background)
    background.addWidget(text('桌面使用系统磨砂效果；系统关闭透明效果或不支持时，显示半透明底色。', 'Subtle'))
    background.addStretch()

    perspective = page('透视')
    perspective.addWidget(text('让文字向远处延伸', 'Section'))
    check(perspective, '启用 3D 透视', 'perspective_enabled')
    studio.checks['perspective_enabled'].setEnabled(a.mode == 'scroll')
    perspective.addWidget(text('3D 只改变侧边列表的外观。取消勾选立即恢复平面；双行布局在“样式”中切换。', 'Subtle'))
    combo(perspective, '靠近你的方向', 'perspective_direction', [('左近右远','left'), ('右近左远','right'), ('上近下远','top'), ('下近上远','bottom')])
    studio.add_slider(perspective, '透视角度', 'perspective_angle', 0, 65, '°')
    studio.add_slider(perspective, '平面旋转', 'roll', -30, 30, '°')
    perspective.addWidget(text('角度 0° 为平面；角度越大，近大远小越明显。可与左、中、右对齐和区域位置自由组合。', 'Subtle'))
    perspective.addStretch()
    studio.update_swatches()
    return tabs
