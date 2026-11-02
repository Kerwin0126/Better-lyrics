# Author: Kerwin
"""Publish an explicitly requested release using an existing GitHub credential.
No credentials are written to files or printed. --publish is required.
"""
import argparse,hashlib,json,os,subprocess,time,urllib.request,urllib.error,urllib.parse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app_info import VERSION
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--publish',action='store_true')
parser.add_argument('--repo',default='Kerwin0126/Better-lyrics')
args=parser.parse_args()
if not args.publish:
    print('No mutation. Add --publish only when ready to upload and publish this version.')
    raise SystemExit(0)

token=os.environ.get('BETTER_LYRICS_GITHUB_TOKEN')
if not token:
    result=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\nusername='+args.repo.split('/')[0]+'\n\n',text=True,capture_output=True,check=True,
                          env=dict(os.environ,GCM_INTERACTIVE='Never',GIT_TERMINAL_PROMPT='0'),timeout=30)
    credential=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    token=credential['password']
HEADERS={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
         'X-GitHub-Api-Version':'2022-11-28','User-Agent':'BetterLyrics-Release'}
base='https://api.github.com/repos/'+args.repo

def api(url,method='GET',body=None,data=None,content_type='application/json'):
    if body is not None:data=json.dumps(body,ensure_ascii=False).encode('utf-8')
    request=urllib.request.Request(url,data=data,headers=dict(HEADERS,**{'Content-Type':content_type}),method=method)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request,timeout=180) as response:return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code<500 or attempt==2:raise
        except (urllib.error.URLError,TimeoutError):
            if attempt==2:raise
        time.sleep(2*(attempt+1))

assets=[ROOT/'.release'/f'BetterLyrics-Setup-{VERSION}-x64.exe']
assets+=sorted((ROOT/'.packaging/compliance-sources').glob('*.tar.xz'))
assert len(assets)==4 and all(p.is_file() for p in assets)
checksums=''.join(hashlib.file_digest(p.open('rb'),'sha256').hexdigest()+'  '+p.name+'\n' for p in assets)
checksum_file=ROOT/'.release/SHA256SUMS.txt';checksum_file.write_text(checksums,encoding='utf-8')
assets.append(checksum_file)
sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
tag='v'+VERSION
releases=api(base+'/releases?per_page=100')
release=next((r for r in releases if r['tag_name']==tag),None)
if release is None:
    release=api(base+'/releases','POST',dict(tag_name=tag,target_commitish=sha,name='Better lyrics | 浮词 '+tag,
        body=(ROOT/'docs'/f'RELEASE_{VERSION}.md').read_text(encoding='utf-8'),draft=True,prerelease=True))
elif not release['draft']:
    raise SystemExit('This release is already public; refusing to overwrite it.')
for path in assets:
    current=api(base+'/releases/'+str(release['id'])+'/assets')
    existing=next((a for a in current if a['name']==path.name),None)
    if existing:
        assert existing['size']==path.stat().st_size,('existing asset size differs',path.name)
        continue
    upload=release['upload_url'].split('{',1)[0]+'?'+urllib.parse.urlencode({'name':path.name})
    result=api(upload,'POST',data=path.read_bytes(),content_type='application/octet-stream')
    assert result['size']==path.stat().st_size
    print('Uploaded',path.name,path.stat().st_size,flush=True)
release=api(base+'/releases/'+str(release['id']),'PATCH',dict(draft=False,prerelease=True))
api(base+'/topics','PUT',dict(names=['better-lyrics','desktop-lyrics','windows','pyside6','qt','kugou','qqmusic','qishui-music','netease-cloud-music','source-available','non-commercial']))
api(base,'PATCH',dict(description='Better lyrics | 浮词 — Windows 透明桌面歌词；酷狗 / QQ / 汽水 / 网易云，逐字变色、3D 透视与动效。作者 kerwin。源码公开，禁止商用。'))
print('Published',release['html_url'],flush=True)
