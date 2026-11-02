# Author: Kerwin
"""Player-specific lyric providers. Network work never runs on the Qt thread."""
from pathlib import Path
import base64, ctypes, gzip, html, json, os, re, sqlite3, struct, string, threading, time, unicodedata, hashlib
import urllib.request, urllib.parse, zlib
from functools import lru_cache
from contextlib import closing
from app_paths import DATA_DIR as APP_DIR, RESOURCE_DIR
from lyric_data import LyricLine, parse_lyrics, decode_file, discover_folder, match_file, scan

PLAYERS = {'kugou':'酷狗音乐', 'soda':'汽水音乐', 'qq':'QQ音乐', 'netease':'网易云音乐'}
RESOLVED_TRACKS={}

class CachePending(ValueError):
    pass

def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKC', value).casefold() if c.isalnum())

def netease_track(title, artist):
    path=Path(os.environ.get('LOCALAPPDATA',''))/'NetEase/CloudMusic/webdata/file/playingList'
    history=path.parents[2]/'Library/webdb.dat'
    try:mtime=path.stat().st_mtime_ns
    except OSError:mtime=0
    try:history_mtime=history.stat().st_mtime_ns
    except OSError:history_mtime=0
    try:history_mtime+=history.with_name(history.name+'-wal').stat().st_mtime_ns
    except OSError:pass
    return _netease_track(str(path),mtime,title,artist,str(history),history_mtime) or RESOLVED_TRACKS.get((normalized(title),normalized(artist)))

@lru_cache(maxsize=24)
def _netease_track(filename,mtime,title,artist,history='',history_mtime=0):
    path=Path(filename)
    playlist_match=None
    try:
        for item in json.loads(path.read_bytes()).get('list',[]):
            track=item.get('track',{})
            if normalized(track.get('name',''))==normalized(title) and normalized('/'.join(a['name'] for a in track.get('artists',[])))==normalized(artist):
                playlist_match=track
                break
    except (OSError,ValueError,KeyError): pass
    if history_mtime:
        try:
            with closing(sqlite3.connect(Path(history).as_uri()+'?mode=ro',uri=True,timeout=.05)) as database:
                for table in ('historyTracks','dbTrack'):
                    order=' order by playtime desc' if table=='historyTracks' else ''
                    for identifier,raw in database.execute('select id,jsonStr from '+table+' where jsonStr like ?'+order+' limit 60',('%'+title+'%',)):
                        track=json.loads(raw)
                        track=track.get('track',track)
                        artists=track.get('artists',track.get('ar',[]))
                        if normalized(track.get('name',''))==normalized(title) and normalized('/'.join(a.get('name','') for a in artists))==normalized(artist):
                            track=dict(track,id=track.get('id',identifier),duration=track.get('duration',track.get('dt',0)))
                            return track
        except (sqlite3.Error,OSError,ValueError,TypeError):pass
    return playlist_match

def resolve_netease(title,artist):
    track=netease_track(title,artist)
    if track:return track
    result=get_json('https://music.163.com/api/search/get',dict(s=title+' '+artist,type=1,limit=20))
    songs=result.get('result',{}).get('songs',[]) if isinstance(result.get('result'),dict) else []
    matches=[s for s in songs if isinstance(s,dict) and normalized(s.get('name',''))==normalized(title) and normalized('/'.join(a.get('name','') for a in s.get('artists',[])))==normalized(artist)]
    if not matches:raise CachePending('尚未取得当前曲目 ID，正在自动重试')
    durations=[s.get('duration',0) for s in matches if s.get('duration',0)>0]
    if durations and max(durations)-min(durations)>2500:
        raise CachePending('发现多个同名版本，等待本地曲目记录以避免歌词错版')
    # Search is a fallback, used only when title and performers agree exactly.
    track=matches[0]
    RESOLVED_TRACKS[(normalized(title),normalized(artist))]=track
    return track

def duration_for(data):
    if data.get('duration_ms',0)>0:return data['duration_ms']
    track=netease_track(data.get('title',''),data.get('artist',''))
    return track.get('duration',0) if track else 0

def qq_folder():
    config=Path(os.environ.get('APPDATA',''))/'Tencent/QQMusic/WebkitCachePath.ini'
    try:
        for encoding in ('utf-8-sig','utf-16','gb18030'):
            try:text=config.read_text(encoding=encoding)
            except UnicodeError:continue
            match=re.search(r'^Path\s*=\s*(.+)',text,re.M)
            if match:
                folder=Path(match[1].strip().strip('"')).parent/'QQMusicLyricNew'
                if folder.is_dir():return folder
    except OSError:pass
    # Probe known cache names at drive roots; never traverse entire disks.
    for letter in string.ascii_uppercase:
        folder=Path(letter+':/QQMusicCache/QQMusicLyricNew')
        if folder.is_dir():return folder
    return None

def parse_word_lyrics(text, kind):
    lines=[]
    for row in text.splitlines():
        match=re.match(r'^\[(\d+),(\d+)\](.*)',row)
        if not match:continue
        start,duration,content=int(match[1]),int(match[2]),match[3]
        if kind=='yrc':
            words=[(int(m[1])-start,int(m[2]),m[3]) for m in re.finditer(r'\((\d+),(\d+),\d+\)(.*?)(?=\(\d+,\d+,\d+\)|$)',content)]
        else:
            words=[(int(m[2])-start,int(m[3]),m[1]) for m in re.finditer(r'(.*?)\((\d+),(\d+)\)',content)]
        lyric=''.join(w[2] for w in words)
        if lyric.strip():lines.append(LyricLine(start,duration,lyric,words))
    if not lines:raise ValueError('未找到字词时间')
    return lines

QMC_KEY=bytes.fromhex('c34ad6ca9067f752d8a166629f5b0900c35e95239f13117ed8923fbc90bb740ec347743d90aa3f51d8f411849fde951dc3c609d59ffa66f9d8f0f7a090a1d6f3c3f3d6a190a0f7f0d8f966fa9fd509c6c31d95de9f8411f4d8513faa903d7447c30e74bb90bc3f92d87e11139f23955ec300095b9f6266a1d852f76790cad64a')

def read_qrc(path):
    raw=path.read_bytes()
    if len(raw)>8*1024*1024:raise ValueError('歌词文件过大')
    if raw[:11]!=bytes.fromhex('9825b0ace3028368e8fc6c'):raise ValueError('不支持的 QRC 缓存格式')
    raw=bytes(value^QMC_KEY[(i if i<=0x7fff else i%0x7fff)&127] for i,value in enumerate(raw))[11:]
    decoder=ctypes.CDLL(str(RESOURCE_DIR/'QrcDecode.dll'))
    decoder.qrc_decrypt.argtypes=[ctypes.c_void_p,ctypes.c_int]
    buffer=ctypes.create_string_buffer(raw,len(raw))
    if decoder.qrc_decrypt(buffer,len(raw))!=0:raise ValueError('QRC 长度错误')
    decompressor=zlib.decompressobj()
    text=decompressor.decompress(buffer.raw,8*1024*1024).decode('utf-8-sig')
    match=re.search(r'LyricContent="(.*?)"\s*/?>',text,re.S)
    if not match:raise ValueError('QRC 缺少歌词')
    return parse_word_lyrics(html.unescape(match[1]),'qrc')

def get_json(url, params):
    request=urllib.request.Request(url+'?'+urllib.parse.urlencode(params),headers={'User-Agent':'FloatingLyrics/0.5 (Windows; Kerwin)','Referer':'https://music.163.com/' if '163.com' in url else 'https://www.kugou.com/'})
    with urllib.request.urlopen(request,timeout=12) as response:
        return json.loads(response.read(8*1024*1024))

def online_krc(data):
    title,artist=data['title'],data['artist']
    result=get_json('https://lyrics.kugou.com/search',dict(ver=1,man='yes',client='pc',keyword=artist+' '+title,duration=int(data.get('duration_ms',0))))
    candidates=[c for c in result.get('candidates',[]) if normalized(c.get('song',''))==normalized(title) and normalized(c.get('singer',''))==normalized(artist) and (not data.get('duration_ms') or abs(c.get('duration',0)-data['duration_ms'])<=2500)]
    if not candidates:raise ValueError('没有歌名、歌手和时长均匹配的在线歌词')
    candidate=min(candidates,key=lambda c:abs(c.get('duration',0)-data.get('duration_ms',0)))
    result=get_json('https://lyrics.kugou.com/download',dict(ver=1,client='pc',id=candidate['id'],accesskey=candidate['accesskey'],fmt='krc',charset='utf8'))
    raw=base64.b64decode(result['content'])
    from lyric_data import KRC_KEY
    packed=bytes(v^KRC_KEY[i%len(KRC_KEY)] for i,v in enumerate(raw[4:]))
    text=zlib.decompressobj().decompress(packed,8*1024*1024)
    return parse_lyrics(text.decode('utf-8-sig'),'.krc')[1], '在线酷狗 KRC · 精确匹配'

def soda_duration_matches(track,data):
    """SMTC reports the audition length while the cache keeps the full song."""
    duration=data.get('duration_ms',0)
    if not duration:return True
    lengths=[track.get('duration',0),(track.get('preview') or {}).get('duration',0),
             (track.get('audition_info') or {}).get('duration_ms',0)]
    return any(length>0 and abs(length-duration)<=2500 for length in lengths)

def fetch(player,data):
    title,artist=data.get('title',''),data.get('artist','')
    if player=='soda':
        from soda_cache import records
        database=Path(os.environ.get('APPDATA',''))/'SodaMusic/LunaCacheV2/entries.db'
        track=None
        try:
            # A recently accessed entry wins over an older same-name recording.
            for record in sorted(records(database),key=lambda r:r.get('previousAccessTime',0),reverse=True):
                detail=record.get('info',{}).get('mediaDetail',{})
                response=detail.get('response',{})
                candidate=response.get('track',{})
                if normalized(candidate.get('name',''))!=normalized(title) or normalized('/'.join(a.get('name','') for a in candidate.get('artists',[])))!=normalized(artist):continue
                if not soda_duration_matches(candidate,data):continue
                if track is None:track=candidate
                lyric=detail.get('lyrics',response.get('lyric',{}))
                content=lyric.get('content','')
                if content:
                    kind='.krc' if re.search(r'^\[\d+,\d+\]',content,re.M) else '.lrc'
                    preview=abs(candidate.get('duration',0)-data.get('duration_ms',0))>2500
                    return parse_lyrics(content,kind)[1],'汽水本地播放缓存'+(' · 试听版' if preview else '')+' · 字词时间'
        except (OSError,ValueError,TypeError,KeyError,struct.error):pass
        queue=Path(os.environ.get('APPDATA',''))/'SodaMusic/LunaStorage/QueueCache'
        if track is None:
            try:
                raw=queue.read_bytes()
                if raw.startswith(b'LUNA'):
                    root=json.loads(gzip.decompress(raw[4:]))
                    for group in root.values():
                        for playable in group.get('playables',[]):
                            candidate=playable.get('track',{})
                            if normalized(candidate.get('name',''))==normalized(title) and normalized('/'.join(a.get('name','') for a in candidate.get('artists',[])))==normalized(artist) and soda_duration_matches(candidate,data):track=candidate;break
            except (OSError,ValueError,TypeError,KeyError):pass
        if not track:
            try:return online_krc(data)
            except Exception:raise CachePending('汽水缓存中暂无歌名、歌手和完整／试听时长匹配的曲目，正在自动重试')
        url='https://music.douyin.com/qishui/share/track?'+urllib.parse.urlencode({'track_id':track['id']})
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(request,timeout=15) as response:page=response.read(4*1024*1024).decode('utf-8')
        marker=page.find('_ROUTER_DATA')
        if marker<0:raise ValueError('汽水分享页未提供歌词数据')
        router=json.JSONDecoder().raw_decode(page[page.index('{',marker):])[0]
        if str(router.get('loaderData',{}).get('track_page',{}).get('track_id',''))!=str(track['id']):
            raise ValueError('汽水分享页返回的曲目 ID 不一致')
        def find_lyrics(node):
            if isinstance(node,dict):
                if isinstance(node.get('lyrics'),dict) and isinstance(node['lyrics'].get('sentences'),list):return node['lyrics']['sentences']
                for value in node.values():
                    result=find_lyrics(value)
                    if result is not None:return result
            elif isinstance(node,list):
                for value in node:
                    result=find_lyrics(value)
                    if result is not None:return result
            return None
        sentences=find_lyrics(router)
        lines=[]
        for sentence in sentences or []:
            start=int(sentence['startMs']);end=int(sentence['endMs']);text=sentence.get('text','')
            words=[(int(w['startMs'])-start,max(0,int(w['endMs'])-int(w['startMs'])),w['text']) for w in sentence.get('words',[])]
            if text.strip():lines.append(LyricLine(start,max(0,end-start),text,words))
        if not lines:raise ValueError('汽水当前歌曲暂无带时间歌词')
        return lines,'汽水曲目 ID · 官方分享页字词时间'
    if player=='qq':
        folder=qq_folder()
        if folder:
            for path in folder.glob('*_qm.qrc'):
                parts=path.stem.removesuffix('_qm').split(' - ',3)
                if len(parts)>=2 and normalized(parts[0])==normalized(artist) and normalized(parts[1])==normalized(title):
                    return read_qrc(path),'QQ 本地 QRC'
    if player=='netease':
        track=resolve_netease(title,artist)
        if track:
            result=get_json('https://music.163.com/api/song/lyric',dict(id=track['id'],lv=-1,yv=-1,tv=-1))
            if result.get('yrc',{}).get('lyric'):
                return parse_word_lyrics(result['yrc']['lyric'],'yrc'),'网易云曲目 ID · YRC'
            if result.get('lrc',{}).get('lyric'):
                return parse_lyrics(result['lrc']['lyric'],'.lrc')[1],'网易云曲目 ID · LRC'
    return online_krc(data)

class LyricProvider:
    def __init__(self):
        self.lock=threading.Lock();self.key=None;self.result=None;self.pending=False;self.retry=0
        self.cache={}
        self.failures={}
    def request(self,player,data):
        key=(player,data['identity'])
        with self.lock:
            if self.key==key and (self.pending or self.result and self.result.get('ok') or time.monotonic()<self.retry):return
            self.key=key;self.result=None;self.pending=True
        def work():
            try:
                saved=APP_DIR/'lyric_cache'/(hashlib.sha256(json.dumps(key,ensure_ascii=False).encode()).hexdigest()+'.json')
                if key in self.cache:lines,source=self.cache[key]
                else:
                    lines=source=None
                    try:
                        cached=json.loads(saved.read_text(encoding='utf-8'))
                        if cached.get('key')==list(key):
                            lines=[LyricLine(l['start_ms'],l['duration_ms'],l['text'],l['words']) for l in cached['lines']]
                            source=cached['source']+' · 已保存'
                            if player=='netease' and cached.get('track'):
                                RESOLVED_TRACKS[(normalized(data.get('title','')),normalized(data.get('artist','')))]=cached['track']
                    except (OSError,ValueError,KeyError,TypeError):pass
                    if not lines:
                        lines,source=fetch(player,data)
                        try:
                            from dataclasses import asdict
                            saved.parent.mkdir(exist_ok=True)
                            temporary=saved.with_suffix('.tmp')
                            track=netease_track(data.get('title',''),data.get('artist','')) if player=='netease' else None
                            if track:track={key:track[key] for key in ('id','name','duration','artists') if key in track}
                            temporary.write_text(json.dumps(dict(key=key,source=source,track=track,lines=[asdict(l) for l in lines]),ensure_ascii=False),encoding='utf-8')
                            temporary.replace(saved)
                        except OSError:pass
                    self.cache[key]=(lines,source)
                    if len(self.cache)>64:self.cache.pop(next(iter(self.cache)))
                result=dict(ok=True,lines=lines,source=source,key=key)
                self.failures.pop(key,None)
            except CachePending as exc:result=dict(ok=False,error=str(exc),key=key,retry_after=2)
            except (urllib.error.URLError,TimeoutError) as exc:
                result=dict(ok=False,error='暂时无法联网获取歌词，稍后自动重试',detail=str(exc),key=key)
            except Exception as exc:result=dict(ok=False,error=str(exc),key=key)
            with self.lock:
                self.failures[key]=self.failures.get(key,0)+1 if not result['ok'] else 0
                if self.key==key:
                    self.result=result;self.pending=False
                    self.retry=time.monotonic()+result.get('retry_after',min(15,2**min(4,self.failures[key])))
        threading.Thread(target=work,daemon=True).start()
    def snapshot(self):
        with self.lock:return self.result
