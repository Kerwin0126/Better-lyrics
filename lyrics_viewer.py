# Author: Kerwin
"""Local KuGou lyrics with read-only playback following."""
from __future__ import annotations

import argparse
from bisect import bisect_right
import json
import os
from pathlib import Path
import re
import time
import unicodedata
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import zlib
from dataclasses import dataclass
from playback_source import PlaybackSource

from lyric_data import (KRC_KEY, MAX_BYTES, LyricLine, decode_file, parse_lyrics,
    discover_folder, scan, short_name, stamp, normalize_identity, match_file, active_line)


class Viewer(tk.Tk):
    def __init__(self, initial: Path | None = None):
        super().__init__()
        self.title('第三方歌词显示器 · 酷狗同步实验')
        self.geometry('1100x680')
        self.minsize(850, 540)
        self.option_add('*Font', ('Microsoft YaHei UI', 10))
        self.folder = tk.StringVar(value=str(initial.parent if initial else discover_folder()))
        self.query = tk.StringVar()
        self.title_text = tk.StringVar(value='选择一份歌词')
        self.detail = tk.StringVar()
        self.status = tk.StringVar(value='等待读取')
        self.source = tk.StringVar()
        self.show_time = tk.BooleanVar(value=True)
        self.follow = tk.BooleanVar(value=True)
        self.playback_text = tk.StringVar(value='正在连接酷狗…')
        self.offset_ms = 0
        self.highlighted = -1
        self.playing_identity = None
        self.retry_at = 0.0
        self.last_debug = 0.0
        self.files: list[Path] = []
        self.visible: list[Path] = []
        self.current: Path | None = None
        self.lines: list[LyricLine] = []
        self.build()
        self.query.trace_add('write', lambda *_: self.filter_files())
        self.refresh(initial)
        self.reader = PlaybackSource()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(80, self.sync_tick)

    def build(self):
        top = ttk.Frame(self, padding=(16, 12))
        top.pack(fill='x')
        ttk.Label(top, text='第三方歌词显示器', font=('Microsoft YaHei UI', 17, 'bold')).pack(anchor='w')
        ttk.Label(top, text='跟随酷狗自动选歌、滚动并高亮当前句；手动选文件会暂停跟随。').pack(anchor='w', pady=(4, 6))
        sync_bar = ttk.Frame(top)
        sync_bar.pack(fill='x', pady=(0, 8))
        ttk.Checkbutton(sync_bar, text='跟随酷狗', variable=self.follow, command=self.reset_follow).pack(side='left')
        ttk.Label(sync_bar, textvariable=self.playback_text, foreground='#235ca7').pack(side='left', padx=16)
        bar = ttk.Frame(top)
        bar.pack(fill='x')
        ttk.Entry(bar, textvariable=self.folder).pack(side='left', fill='x', expand=True)
        ttk.Button(bar, text='选择目录', command=self.pick_folder).pack(side='left', padx=6)
        ttk.Button(bar, text='刷新列表', command=self.refresh).pack(side='left')
        ttk.Button(bar, text='打开文件…', command=self.pick_file).pack(side='left', padx=(6, 0))

        body = ttk.Panedwindow(self, orient='horizontal')
        left = ttk.Frame(body, padding=(0, 4, 10, 0))
        right = ttk.Frame(body, padding=(10, 4, 0, 0))
        body.add(left, weight=1)
        body.add(right, weight=3)
        ttk.Label(left, text='本地缓存（按文件修改时间排序）').pack(anchor='w', pady=(0, 8))
        ttk.Entry(left, textvariable=self.query).pack(fill='x', pady=(0, 8))
        list_area = ttk.Frame(left)
        list_area.pack(fill='both', expand=True)
        self.listbox = tk.Listbox(list_area, width=33, activestyle='none', exportselection=False,
                                  borderwidth=0, highlightthickness=1, selectbackground='#2865c7')
        scroll = ttk.Scrollbar(list_area, orient='vertical', command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.listbox.pack(side='left', fill='both', expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.selected)
        ttk.Label(right, textvariable=self.title_text, font=('Microsoft YaHei UI', 15, 'bold'), wraplength=650).pack(anchor='w')
        ttk.Label(right, textvariable=self.detail, wraplength=650).pack(anchor='w', pady=(3, 6))
        ttk.Checkbutton(right, text='显示每句时间戳', variable=self.show_time, command=self.render).pack(anchor='w', pady=(0, 8))
        self.text = ScrolledText(right, height=12, wrap='word', state='disabled', relief='flat', padx=16, pady=12,
                                 bg='#f5f7fa', fg='#17202e', font=('Microsoft YaHei UI', 12), spacing3=10)
        self.text.tag_configure('time', foreground='#7b8391', font=('Consolas', 10))
        self.text.tag_configure('active', background='#dbeafe', foreground='#124a9e')
        self.text.pack(fill='both', expand=True)
        bottom = ttk.Frame(self, padding=(16, 10))
        bottom.pack(side='bottom', fill='x')
        ttk.Label(bottom, textvariable=self.status, foreground='#235ca7').pack(anchor='w')
        ttk.Label(bottom, textvariable=self.source, wraplength=1060, foreground='#6c7480').pack(anchor='w', pady=(4, 0))
        body.pack(fill='both', expand=True, padx=16)

    def pick_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder.get(), title='选择酷狗歌词目录')
        if folder:
            self.folder.set(folder)
            self.query.set('')
            self.refresh()
            self.reset_follow()

    def pick_file(self):
        filename = filedialog.askopenfilename(initialdir=self.folder.get(), filetypes=[('歌词', '*.krc *.lrc'), ('所有文件', '*.*')])
        if filename:
            self.follow.set(False)
            self.load(Path(filename))

    def refresh(self, initial=None):
        try:
            self.files = scan(Path(self.folder.get()))
            self.filter_files()
            target = initial or self.current
            if target not in self.files:
                target = self.files[0] if self.files else None
            if target:
                self.load(target)
                if target in self.visible:
                    index = self.visible.index(target)
                    self.listbox.selection_clear(0, 'end')
                    self.listbox.selection_set(index)
                    self.listbox.see(index)
            else:
                self.lines = []
                self.current = None
                self.title_text.set('未发现歌词文件')
                self.detail.set('请先在酷狗中播放歌曲，或手动选择歌词目录。')
                self.source.set('')
                self.status.set('当前目录没有 .krc / .lrc 文件')
                self.render()
        except (OSError, ValueError) as exc:
            self.status.set(f'扫描失败：{exc}')

    def filter_files(self):
        needle = self.query.get().strip().casefold()
        self.visible = [p for p in self.files if needle in p.name.casefold()]
        self.listbox.delete(0, 'end')
        for p in self.visible:
            self.listbox.insert('end', short_name(p))

    def selected(self, _event=None):
        selected = self.listbox.curselection()
        if selected:
            self.follow.set(False)
            self.load(self.visible[selected[0]])

    def load(self, path, quiet=False):
        try:
            meta, lines = parse_lyrics(decode_file(path), path.suffix)
            self.current, self.lines = path, lines
            self.offset_ms = int(meta.get('offset', '0'))
            self.title_text.set(meta.get('ti') or short_name(path))
            artist = meta.get('ar') or '未提供歌手信息'
            self.detail.set(f'{artist}  ·  {path.suffix[1:].upper()}  ·  {len(lines)} 句  ·  {sum(len(x.words) for x in lines)} 个逐字/词时间片')
            self.source.set(f'实际读取文件：{path}')
            self.status.set(f'读取成功 · 缓存共 {len(self.files)} 份')
            self.render()
            return True
        except (OSError, ValueError, zlib.error) as exc:
            self.status.set(f'读取失败：{path.name}')
            if not quiet:
                messagebox.showerror('无法读取歌词', str(exc), parent=self)
            return False

    def render(self):
        self.highlighted = -1
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        for line in self.lines:
            if self.show_time.get():
                self.text.insert('end', f'{stamp(line.start_ms)}  ', 'time')
            self.text.insert('end', line.text + '\n')
        self.text.configure(state='disabled')
        self.text.yview_moveto(0)

    def reset_follow(self):
        self.playing_identity = None
        self.retry_at = 0.0

    def clear_highlight(self):
        self.text.tag_remove('active', '1.0', 'end')
        self.highlighted = -1

    def show_waiting(self, identity, reason):
        self.current = None
        self.lines = []
        self.offset_ms = 0
        self.title_text.set(identity)
        self.detail.set(reason)
        self.source.set('歌词仍从本地缓存读取；新歌缓存生成后会自动重试。')
        self.render()

    def sync_tick(self):
        try:
            self.update_sync()
        except Exception as exc:
            # Keep the window usable if a file is being written or the player exits.
            self.clear_highlight()
            self.status.set(f'同步暂不可用：{exc}')
        finally:
            self.after(80, self.sync_tick)

    def update_sync(self):
        now = time.monotonic()
        data, received = self.reader.snapshot()
        if not self.follow.get():
            self.playback_text.set('手动查看 · 勾选“跟随酷狗”可恢复同步')
            self.clear_highlight()
            return
        if not data or now - received > 3 or not data.get('ok'):
            self.clear_highlight()
            reason = (data or {}).get('error', '正在等待酷狗播放状态')
            if data and now - received > 3:
                reason = '播放状态更新超时，等待恢复；可尝试展开酷狗主窗口'
            self.playback_text.set(reason)
            self.status.set('未获得有效播放位置，歌词已停止跟随')
            return
        identity = data['identity']
        position = data['position_ms']
        state = {'playing': '播放中', 'paused': '已暂停', 'unknown': '状态未知'}[data['state']]
        self.playback_text.set(f'{state}  {stamp(position)} / {stamp(data["duration_ms"])}  ·  进度精度约 1 秒')
        if identity != self.playing_identity:
            self.playing_identity = identity
            self.retry_at = 0
            self.show_waiting(identity, '正在匹配本地歌词…')
        if self.current is None and now >= self.retry_at:
            self.retry_at = now + 1.5
            self.files = scan(Path(self.folder.get()))
            self.filter_files()
            target = match_file(self.files, identity)
            if target:
                if not self.load(target, quiet=True):
                    self.current = None
                if target in self.visible:
                    idx = self.visible.index(target)
                    self.listbox.selection_clear(0, 'end')
                    # selection_set does not generate a mouse-selection event.
                    self.listbox.selection_set(idx)
                    self.listbox.see(idx)
            else:
                self.detail.set('未找到这首歌/版本的本地歌词；等待酷狗生成缓存。')
        index = active_line(self.lines, position + self.offset_ms)
        if index != self.highlighted:
            self.clear_highlight()
            if index >= 0:
                self.text.tag_add('active', f'{index + 1}.0', f'{index + 2}.0')
                self.text.see(f'{index + 1}.0')
            self.highlighted = index
        self.status.set('已同步 · 读取酷狗界面时间 · ' + ('当前句自动高亮' if self.current else '等待本地歌词'))
        if now - self.last_debug > 0.5:
            self.last_debug = now
            debug = dict(data, matched_file=str(self.current) if self.current else None,
                         highlighted_line=index, lyric_start_ms=self.lines[index].start_ms if index >= 0 else None)
            try:
                destination = Path(__file__).with_name('sync_state.json')
                temp = destination.with_suffix('.tmp')
                temp.write_text(json.dumps(debug, ensure_ascii=False, indent=2), encoding='utf-8')
                temp.replace(destination)
            except OSError:
                pass

    def close(self):
        self.reader.close()
        self.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path)
    parser.add_argument('--inspect', type=Path, help='Parse one file and print metadata/counts without opening UI')
    args = parser.parse_args()
    if args.inspect:
        meta, lines = parse_lyrics(decode_file(args.inspect), args.inspect.suffix)
        print(json.dumps({'file': str(args.inspect), 'title': meta.get('ti'), 'artist': meta.get('ar'),
                          'lines': len(lines), 'word_segments': sum(len(x.words) for x in lines),
                          'first_ms': lines[0].start_ms, 'last_ms': lines[-1].start_ms}, ensure_ascii=True))
    else:
        Viewer(args.file).mainloop()


if __name__ == '__main__':
    main()
