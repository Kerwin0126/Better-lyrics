# Author: Kerwin
"""Regressions for cache-only lyrics and metadata/progress decoupling."""
import json,struct,time,os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sqlite3
from contextlib import closing
from soda_cache import records,Records
from player_lyrics import fetch,netease_track,soda_duration_matches
from playback_source import PlaybackSource

def packed_string(s):
    b=s.encode();return bytes([0xa0+len(b)])+b
def payload(s):return b'\xd4\x72\x40\x91'+packed_string('value')+packed_string(s)
def page(number,value):
    b=bytearray(4096);struct.pack_into('<Q',b,0,number);struct.pack_into('<HH',b,18,2,2)
    raw=payload(value);node=struct.pack('<IHH',len(raw),0,1)+b'k'+raw
    offset=4096-24-len(node);struct.pack_into('<H',b,24,offset);b[24+offset:24+offset+len(node)]=node
    return b
with TemporaryDirectory() as folder:
    root=Path(folder);data=bytearray(4*4096)
    for offset,revision,page_no in ((0,1,2),(4096,2,3)):
        struct.pack_into('<II',data,offset+24,0xbeefc0de,2);struct.pack_into('<Q',data,offset+136,page_no);struct.pack_into('<Q',data,offset+152,revision)
    data[8192:12288]=page(2,'old');data[12288:]=page(3,'new')
    file=root/'entries.db';file.write_bytes(data)
    assert list(records(file))==[{'value':'new'}],'must read the latest committed DB root'
    file.write_bytes(b'bad')
    try:list(records(file));raise AssertionError('corrupt DB accepted')
    except ValueError:pass
    local=root/'profile';dbfile=local/'NetEase/CloudMusic/Library/webdb.dat';dbfile.parent.mkdir(parents=True)
    with closing(sqlite3.connect(dbfile)) as db:
        db.execute('create table historyTracks(id text,jsonStr text,playtime integer)');db.execute('create table dbTrack(id text,jsonStr text)')
        db.execute('insert into historyTracks values (?,?,?)',('42',json.dumps(dict(id=42,name='Test Song',artists=[dict(name='Singer')],duration=123456)),1))
        db.commit()
    with patch.dict(os.environ,{'LOCALAPPDATA':str(local)}):
        assert netease_track('Test Song','Singer')['duration']==123456,'must resolve history without playingList'

entry=dict(info=dict(mediaDetail=dict(response=dict(track=dict(name='Song',artists=[dict(name='Singer')],duration=3000)),lyrics=dict(content='[0,3000]<0,1000,0>One<1000,2000,0>Two'))))
with patch('soda_cache.records',return_value=iter([entry])),patch('urllib.request.urlopen',side_effect=AssertionError('network must not be used')):
    lines,source=fetch('soda',dict(title='Song',artist='Singer',duration_ms=3000))
    assert lines[0].text=='OneTwo' and len(lines[0].words)==2 and '本地' in source

track=entry['info']['mediaDetail']['response']['track']
track.update(duration=252162,preview=dict(duration=60047),audition_info=dict(duration_ms=60047))
with patch('soda_cache.records',return_value=iter([entry])),patch('urllib.request.urlopen',side_effect=AssertionError('preview lyrics must remain offline')):
    lines,source=fetch('soda',dict(title='Song',artist='Singer',duration_ms=60000))
    assert lines[0].text=='OneTwo' and '试听版' in source,'60s audition must accept its own full-song lyric cache'
assert not soda_duration_matches(track,dict(duration_ms=45000)),'unrelated durations must still be rejected'
assert not soda_duration_matches(dict(duration=252162),dict(duration_ms=60000)),'a short timeline alone is not proof of a preview version'
assert not soda_duration_matches(dict(duration=252162,preview=None,audition_info=None),dict(duration_ms=60000))

class Reader:
    def __init__(self,value):self.value=value
    def snapshot(self):return self.value,time.monotonic()
reader=PlaybackSource.__new__(PlaybackSource);reader.selected='netease'
reader.media=Reader(dict(players=dict(netease=dict(running=True,ok=True,title='Song',artist='Singer',identity='Singer - Song',duration_ms=0,timeline_valid=False))))
reader.accessible=Reader(dict(ok=False,error='progress unavailable'))
data,stamp=reader.snapshot()
assert data['ok'] and not data['progress_ok'] and data['identity']=='Singer - Song','missing progress must not suppress song/lyrics'

reader.media=Reader(dict(players=dict(netease=dict(running=True,ok=False))))
reader.accessible=Reader(dict(ok=True,window_title="Devil's Angel - MINNIE",state='playing',
                              source='MSAA progress geometry',progress_fraction=.4))
with patch('player_lyrics.duration_for',return_value=168000):
    data,stamp=reader.snapshot()
assert data['ok'] and data['progress_ok'] and data['identity']=="MINNIE - Devil's Angel" and data['position_ms']==67200,'NetEase must work with zero SMTC sessions'
reader.media=Reader({})
reader.media.snapshot=lambda:({},0)
with patch('player_lyrics.duration_for',return_value=168000):
    data,stamp=reader.snapshot()
assert data['ok'] and data['progress_ok'] and time.monotonic()-stamp<1,'NetEase native metadata/progress must survive the unrelated media reader being unavailable'
print('PASS: newest LMDB commit only; corrupt database rejected; NetEase history without playingList; Soda lyrics offline without QueueCache/share page; metadata retained while progress unavailable')
