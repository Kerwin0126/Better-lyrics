# Author: Kerwin
"""Read-only integration check against the four currently running players."""
import time
from playback_source import PlaybackSource
from player_lyrics import fetch,PLAYERS
from lyric_data import discover_folder,scan,match_file,decode_file,parse_lyrics
reader=PlaybackSource()
try:
    for player in PLAYERS:
        reader.set_player(player)
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            data,stamp=reader.snapshot()
            if data and data.get('ok') and data.get('progress_ok',True):break
            time.sleep(.2)
        assert data and data.get('ok'),(player,data)
        assert 0<=data['position_ms']<=data['duration_ms'] and data['duration_ms']>0
        if player=='kugou':
            path=match_file(scan(discover_folder()),data['identity'])
            assert path
            lines=parse_lyrics(decode_file(path),path.suffix)[1];source='local KRC'
        else:lines,source=fetch(player,data)
        assert lines and any(line.words for line in lines),(player,'missing timed words')
        print(player,'OK',data['identity'],round(data['position_ms']),len(lines),'lines',source,flush=True)
finally:reader.close()
