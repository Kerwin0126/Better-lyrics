# Author: Kerwin
"""Sparse SMTC anchors must keep moving without false rewinds or freezes."""
from timeline_clock import SodaTimeline
from lyric_renderer import PlaybackClock

def sample(clock,at,raw=10000,stamp=100000,age=0,state='playing',song='song'):
    return clock.project(dict(identity=song,position_ms=raw,duration_ms=240000,
                             timeline_updated_ms=stamp,timeline_age_ms=age,state=state),at)

source=SodaTimeline();display=PlaybackClock();previous=-1
for tick in range(120*60):
    at=10+tick/60
    received=10+(tick//15)*.25
    data=sample(source,received,age=(received-10)*1000)
    display.accept(data,received)
    position=display.position(at)
    assert position>=previous-.001,('false rewind',tick,position,previous)
    previous=position
assert 129000<previous<131000,'two minutes with one timeline anchor must not freeze'

source=SodaTimeline()
sample(source,10,raw=10000)
before=sample(source,15,age=5000)['position_ms']
paused=sample(source,15.1,state='paused',age=5100)['position_ms']
assert paused>=before
assert sample(source,30,state='paused',age=20000)['position_ms']==paused
resumed=sample(source,31,state='playing',stamp=120000,age=0)['position_ms']
assert resumed==paused,'resume can update timestamp before its old position'
assert sample(source,35,state='playing',stamp=120000,age=4000)['position_ms']>=resumed+3999

source=SodaTimeline()
sample(source,10,raw=50000,stamp=100000)
sample(source,15,raw=55000,stamp=105000)
outdated=sample(source,16,raw=10000,stamp=90000)['position_ms']
assert outdated>=55999,'out-of-order anchor must be ignored'
back=sample(source,17,raw=20000,stamp=107000)['position_ms']
assert back==20000,'a fresh backward seek must take effect'
forward=sample(source,18,raw=80000,stamp=108000)['position_ms']
assert forward==80000,'a fresh forward seek must take effect'
assert sample(source,19,raw=0,stamp=109000,song='next')['position_ms']==0
assert sample(SodaTimeline(),10,raw=10000,age=9999999)['position_ms']==10000
print('PASS: 120 seconds / 7200 frames without rewinds or freeze; pause/resume with old anchor; stale anchor rejection; real seeks; track reset; implausible timestamp rejected')
