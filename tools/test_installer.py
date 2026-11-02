# Author: Kerwin
"""Install into an isolated Chinese/spaced path, launch without Python on PATH,
then uninstall. This is a local smoke test, not a clean Windows VM test.
"""
from pathlib import Path
import os,sys,subprocess,time,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app_info import VERSION
base=ROOT/'.packaging/install-smoke'
target=(base/'安装验证 目录').resolve()
profile=(base/'Profile').resolve()
base.mkdir(parents=True,exist_ok=True)
if not str(target).startswith(str(base.resolve())+os.sep):raise RuntimeError('Invalid test target')
installer=ROOT/'.release'/f'BetterLyrics-Setup-{VERSION}-x64.exe'
cmd=[str(installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',
     '/TASKS=',f'/DIR={target}',f'/LOG={base.resolve()/"install.log"}']
subprocess.run(cmd,check=True,timeout=120)
assert (target/'installed.flag').is_file()
assert (target/'_internal/python314.dll').is_file()
assert (target/'_internal/msvcp140.dll').is_file()
assert (target/'_internal/PySide6/Qt6Widgets.dll').is_file()
data=profile/'BetterLyrics';data.mkdir(parents=True,exist_ok=True)
(data/'appearance.json').write_text(json.dumps(dict(player='netease',visible=False)),encoding='utf-8')
env=dict(os.environ,LOCALAPPDATA=str(profile),PATH=os.environ['WINDIR']+'\\System32',
         PYTHONPATH='',PYTHONHOME='')
process=subprocess.Popen([str(target/'浮词.exe')],cwd=target,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        if process.poll() is not None:raise RuntimeError('Installed application exited: '+str(process.returncode))
        if (data/'sync_state.json').is_file():break
        time.sleep(.2)
    row=json.loads((data/'sync_state.json').read_text(encoding='utf-8'))
    assert row['player']=='netease','saved source must initialize without radio toggles'
    print(json.dumps(dict(installed=True,pid=process.pid,custom_path=True,isolated_data=True,
                          stripped_path=True,source=row['player']),ensure_ascii=True),flush=True)
    (base/'runtime-test.json').write_text(json.dumps(dict(pid=process.pid,exe=str(target/'浮词.exe')),ensure_ascii=False),encoding='utf-8')
    query="[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); (Get-Process -Id "+str(process.pid)+").Modules | Where-Object {$_.ModuleName -match '^(python3|Qt6|msvcp|vcruntime)'} | Select-Object ModuleName,FileName | ConvertTo-Json -Compress"
    output=subprocess.check_output(['powershell.exe','-NoProfile','-Command',query],encoding='utf-8')
    modules=json.loads(output)
    (base/'runtime-modules.json').write_text(json.dumps(modules,ensure_ascii=False,indent=2),encoding='utf-8')
    for required in ['python314.dll','Qt6Core.dll','msvcp140.dll']:
        matches=[m for m in modules if m['ModuleName'].lower()==required.lower()]
        assert matches and any(m['FileName'].lower().startswith(str(target).lower()+os.sep) for m in matches),('runtime not loaded from app directory',required)
finally:
    # Only terminate this test instance and its own helper children.
    subprocess.run(['taskkill.exe','/PID',str(process.pid),'/T','/F'],capture_output=True)
uninstaller=target/'unins000.exe'
subprocess.run([str(uninstaller),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',
                f'/LOG={base.resolve()/"uninstall.log"}'],check=True,timeout=90)
for _ in range(25):
    if not (target/'浮词.exe').exists():break
    time.sleep(.2)
assert not (target/'浮词.exe').exists()
assert (data/'appearance.json').exists(),'uninstall must preserve user data'
print('PASS: custom install; complete runtime; launch without Python PATH; separate writable data; saved source; uninstall and data preservation',flush=True)
