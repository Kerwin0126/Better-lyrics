# Author: Kerwin
"""Sample the running viewer's diagnostic output during a short playback check."""
import json
from pathlib import Path
import time

path = Path(__file__).with_name('sync_state.json')
samples = []
until = time.monotonic() + 4
while time.monotonic() < until:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not samples or data['sampled_unix_ms'] != samples[-1]['sampled_unix_ms']:
        samples.append(data)
    time.sleep(.2)
assert len(samples) >= 2, '播放状态没有持续更新'
assert all(row.get('matched_file') for row in samples), '未匹配歌词'
assert all(-1500 <= row['estimated_position_ms'] - row['position_ms'] <= 1500 for row in samples), '进度插值越界'
assert any(row['estimated_position_ms'] % 1000 for row in samples if row['state']=='playing'), '播放时未产生平滑插值'
print(json.dumps([{'raw':s['position_ms'],'display':s['estimated_position_ms'],
                   'line':s['highlighted_line'],'state':s['state']} for s in samples]))
print('PASS: live updates, local lyric match, bounded sub-second animation position')
