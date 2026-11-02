# Author: Kerwin
"""Read the local player's state in a worker process, without blocking Tk."""
import json
from pathlib import Path
import subprocess
import threading
import time
from app_paths import APP_DIR, RESOURCE_DIR
from timeline_clock import SodaTimeline


class JsonReader:
    def __init__(self, binary='PlaybackReader.exe', arguments=()):
        self.binary, self.arguments = binary, arguments
        self.latest = None
        self.received_at = 0.0
        self.process = None
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.process_started=time.monotonic()
        threading.Thread(target=self.run, daemon=True).start()
        threading.Thread(target=self.watchdog,daemon=True).start()

    def watchdog(self):
        while not self.stop.wait(1):
            process=self.process
            if process and process.poll() is None and time.monotonic()-max(self.process_started,self.received_at)>6:
                try:process.terminate()
                except OSError:pass

    def publish(self, value):
        if 'players' in value:
            sampled=int(time.time()*1000)
            for row in value['players'].values():row['sampled_unix_ms']=sampled
        with self.lock:
            self.latest, self.received_at = value, time.monotonic()

    def snapshot(self):
        with self.lock:
            return self.latest, self.received_at

    def run(self):
        base = APP_DIR
        flags = subprocess.CREATE_NO_WINDOW
        while not self.stop.is_set():
            try:
                reader = base / self.binary
                if not reader.is_file():
                    reader = RESOURCE_DIR / self.binary
                if not reader.is_file():
                    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                                    '-File', str(base / 'build_reader.ps1')],
                                   creationflags=flags, check=True, capture_output=True, timeout=30)
                    reader = base / 'PlaybackReader.exe'
                process = subprocess.Popen([str(reader), *self.arguments], stdout=subprocess.PIPE,
                                           stderr=subprocess.DEVNULL, encoding='utf-8', creationflags=flags)
                self.process = process
                self.process_started=time.monotonic()
                if self.stop.is_set():
                    process.terminate()
                    return
                for line in process.stdout:
                    if self.stop.is_set():
                        break
                    try:
                        self.publish(json.loads(line))
                    except ValueError:
                        continue
                if not self.stop.is_set():
                    self.publish({'ok': False, 'error': '播放状态读取器已退出，正在重连'})
            except (OSError, subprocess.SubprocessError) as exc:
                self.publish({'ok': False, 'error': str(exc)})
            finally:
                if self.process and self.process.poll() is None:
                    try:self.process.terminate()
                    except OSError:pass
                self.process = None
            self.stop.wait(1)

    def close(self):
        self.stop.set()
        process = self.process
        if process and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass


class PlaybackSource:
    """Keep player selection explicit; never use the globally active media session."""
    def __init__(self):
        self.media = JsonReader('MediaReader.exe')
        self.selected = None
        self.accessible = None
        self.soda_clock=SodaTimeline()
        self.set_player('kugou')

    def set_player(self, player):
        if player == self.selected:return
        if self.accessible:self.accessible.close()
        self.selected=player
        self.soda_clock=SodaTimeline()
        self.accessible=JsonReader(arguments=['--netease'] if player=='netease' else []) if player in ('kugou','netease') else None

    def statuses(self):
        data,received=self.media.snapshot()
        if time.monotonic()-received>5:return {}
        return (data or {}).get('players',{})

    def snapshot(self):
        media,received=self.media.snapshot()
        rows=(media or {}).get('players',{})
        media_fresh=time.monotonic()-received<=5
        row=dict(rows.get(self.selected,{})) if media_fresh else {}
        if self.selected!='netease' and (not media_fresh or not row.get('running')):
            return dict(ok=False,error='所选播放器未打开或检测超时'),received
        if self.selected=='kugou':
            return self.accessible.snapshot()
        if self.selected=='netease':
            if row.get('ok') and row.get('timeline_valid'):
                row['progress_ok']=True
                return row,received
            value,stamp=self.accessible.snapshot()
            # The player can disable/omit its Windows media session entirely.
            # Its native main-window caption still identifies the current track.
            caption=(value or {}).get('window_title','').strip()
            title,separator,artist=caption.rpartition(' - ')
            metadata_received=received
            if separator and title.strip() and artist.strip() and time.monotonic()-stamp<=4:
                if row.get('title')!=title.strip() or row.get('artist')!=artist.strip():row['duration_ms']=0
                row.update(ok=True,running=True,title=title.strip(),artist=artist.strip(),
                           identity=artist.strip()+' - '+title.strip(),state=value.get('state','paused'))
                metadata_received=stamp
            if not row.get('ok'):return dict(ok=False,error='等待网易云主窗口提供当前歌曲信息'),stamp
            row['progress_ok']=False
            row['source']='网易云辅助功能'
            if not value or not value.get('ok'):
                row.update(error=(value or {}).get('error','正在读取网易云进度'),
                           reader_detail=(value or {}).get('reader_detail',''),position_ms=0)
                return row,metadata_received
            # Resolve duration independently of the Windows media session.
            from player_lyrics import duration_for
            duration=duration_for(row)
            if not duration:
                row.update(error='歌曲已识别，正在补全时长；歌词会独立获取',position_ms=0)
                return row,metadata_received
            row.update(position_ms=round(value['progress_fraction']*duration),duration_ms=duration,
                       source=value['source'],precision='fraction',state=value['state'],ok=True,progress_ok=True,
                       sampled_unix_ms=value.get('sampled_unix_ms',row.get('sampled_unix_ms')))
            return row,min(stamp,metadata_received)
        if not row.get('ok') or not row.get('timeline_valid'):
            return dict(ok=False,error='播放器已打开，等待有效的歌曲和进度信息'),received
        if self.selected=='soda':row=self.soda_clock.project(row,received)
        return row,received

    def close(self):
        self.media.close()
        if self.accessible:self.accessible.close()
