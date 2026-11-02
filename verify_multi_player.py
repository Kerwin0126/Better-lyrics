# Author: Kerwin
"""Offline regressions for source switching, disconnection and stale network results."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import threading,time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
import desktop_lyrics as ui
import player_lyrics as providers
from lyric_data import LyricLine

app=QApplication([])
class Reader:
    selected='kugou'
    def set_player(self,p):self.selected=p
    def statuses(self):return {key:dict(running=True,ok=True,timeline_valid=True) for key in providers.PLAYERS}
    def snapshot(self):
        if hasattr(self,'data'):return self.data,time.monotonic()
        return dict(ok=False,error='test disconnected'),time.monotonic()
    def close(self):pass
with TemporaryDirectory() as folder,patch.object(ui,'BASE',Path(folder)),patch.object(ui,'PlaybackSource',Reader),patch.object(ui.Appearance,'load',classmethod(lambda cls:cls())),patch.object(ui.Appearance,'save',lambda self:None):
    studio=ui.Studio();studio.timer.stop();studio.save_timer.stop()
    assert len(studio.source_radios)==4 and studio.source_group.exclusive()
    for player in ('qq','soda','netease','kugou'):
        studio.lines=[LyricLine(0,1000,'obsolete',[])]
        studio.overlay.set_sequence(studio.lines,0,200,snap=True)
        studio.source_radios[player].setChecked(True)
        assert studio.appearance.player==player and studio.reader.selected==player
        assert not studio.lines and 'obsolete' not in studio.overlay.current
        assert sum(r.isChecked() for r in studio.source_radios.values())==1
    studio.lines=[LyricLine(0,1000,'old',[])];studio.identity='previous';studio.update_playback()
    assert not studio.lines and studio.identity is None
    studio.select_player('soda')
    studio.reader.data=dict(ok=True,identity='Artist - Song',title='Song',artist='Artist',position_ms=2002.721,duration_ms=220031.995,state='paused',precision='timeline')
    studio.identity='Artist - Song';studio.lines=[LyricLine(0,3000,'test',[])];studio.current_file=__import__('pathlib').Path('test')
    studio.update_playback()
    assert studio.clock.text()=='00:02  /  03:40','fractional media durations must format as a clock'
    studio.quit()

for selected in providers.PLAYERS:
    with TemporaryDirectory() as folder,patch.object(ui,'BASE',Path(folder)),patch.object(ui,'PlaybackSource',Reader),patch.object(ui.Appearance,'load',classmethod(lambda cls,p=selected:cls(player=p))),patch.object(ui.Appearance,'save',lambda self:None):
        studio=ui.Studio();studio.timer.stop();studio.save_timer.stop()
        assert studio.reader.selected==selected,'startup must bind the saved source without radio toggles'
        assert studio.source_radios[selected].isChecked()
        assert providers.PLAYERS[selected] in studio.track_title.text()
        assert providers.PLAYERS[selected] in studio.overlay.current
        assert providers.PLAYERS[selected] in studio.preview.current
        studio.update_playback()
        assert providers.PLAYERS[selected] in studio.overlay.current
        studio.quit()

started=threading.Event();release=threading.Event()
def fake_fetch(player,data):
    if data['identity']=='old':started.set();release.wait(3)
    return [LyricLine(0,2000,data['identity'],[])],player
with TemporaryDirectory() as folder,patch.object(providers,'APP_DIR',Path(folder)),patch.object(providers,'fetch',fake_fetch):
    provider=providers.LyricProvider()
    provider.request('qq',{'identity':'old'})
    assert started.wait(1)
    provider.request('soda',{'identity':'new'})
    deadline=time.monotonic()+2
    while provider.snapshot() is None and time.monotonic()<deadline:time.sleep(.01)
    release.set();time.sleep(.05)
    result=provider.snapshot()
    assert result['key']==('soda','new') and result['lines'][0].text=='new'

q=providers.parse_word_lyrics('[1000,1000]甲(1000,300)乙(1500,500)','qrc')[0]
y=providers.parse_word_lyrics('[1000,1000](1000,300,0)甲(1500,500,0)乙','yrc')[0]
assert q.words==y.words==[(0,300,'甲'),(500,500,'乙')]
assert providers.parse_word_lyrics('[0,1000]hello (oh)(0,1000)','qrc')[0].text=='hello (oh)'
assert providers.parse_word_lyrics('[0,1000](0,1000,0)hello (oh)','yrc')[0].text=='hello (oh)'
print('PASS: four exclusive source radios; persisted selection; old lyrics cleared on source switch/disconnect; stale network result rejected; absolute QRC/YRC word times normalized')
