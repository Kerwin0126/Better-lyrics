# Author: Kerwin
"""Collect upstream notices and exact Qt source archives for redistribution."""
from pathlib import Path
import sys,urllib.request,tarfile,hashlib,json,shutil,concurrent.futures,ssl
import importlib.metadata as metadata
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'third_party/licenses'
CACHE=ROOT/'.packaging/compliance-sources'
SOURCES={
    'qtbase':'https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtbase-everywhere-src-6.12.0.tar.xz',
    'qtsvg':'https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtsvg-everywhere-src-6.12.0.tar.xz',
    'pyside':'https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz',
}

def download(url,path):
    if path.is_file() and path.stat().st_size:return
    temporary=path.with_name(path.name+'.part')
    request=urllib.request.Request(url,headers={'User-Agent':'BetterLyrics-Release/0.6 (Kerwin)'})
    with urllib.request.urlopen(request,timeout=60) as response,temporary.open('wb') as target:
        shutil.copyfileobj(response,target)
    temporary.replace(path)

def collect_source(item):
    key,url=item
    archive=CACHE/url.rsplit('/',1)[1]
    download(url,archive)
    sha=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
    notices=[]
    with tarfile.open(archive,'r:xz') as bundle:
        for member in bundle:
            lower=member.name.lower();name=Path(lower).name
            notice=('/licenses/' in lower or name.startswith(('license','copying','copyright','notice')) or name=='qt_attribution.json')
            if not member.isfile() or not notice or member.size>2_000_000:continue
            parts=Path(member.name).parts[1:]
            if not parts or '..' in parts:continue
            relative=Path(key,*parts)
            target=OUT/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            with bundle.extractfile(member) as data:target.write_bytes(data.read())
            notices.append(str(relative).replace('\\','/'))
    print(key,'source and',len(notices),'notices ready',flush=True)
    return dict(component=key,version='6.12.0',url=url,archive=archive.name,sha256=sha,notices=notices)

def main():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        sources=list(pool.map(collect_source,SOURCES.items()))
    python_license=Path(sys.base_prefix)/'LICENSE.txt'
    shutil.copyfile(python_license,OUT/'Python-LICENSE.txt')
    for package in ['PyInstaller','pillow','packaging','shiboken6','PySide6_Essentials']:
        try:dist=metadata.distribution(package)
        except metadata.PackageNotFoundError:continue
        for file in dist.files or []:
            name=Path(str(file)).name.lower()
            if ('dist-info' in str(file) or 'egg-info' in str(file)) and (name.startswith(('license','copying','notice')) or '/licenses/' in str(file).replace('\\','/')):
                source=Path(dist.locate_file(file))
                if source.is_file():shutil.copyfile(source,OUT/(package+'-'+source.name))
    for filename,url in {
        'LGPL-3.0-only.txt':'https://raw.githubusercontent.com/qt/qtbase/v6.12.0/LICENSES/LGPL-3.0-only.txt',
        'GPL-3.0-only.txt':'https://raw.githubusercontent.com/qt/qtbase/v6.12.0/LICENSES/GPL-3.0-only.txt',
        'OpenSSL-LICENSE.txt':'https://raw.githubusercontent.com/openssl/openssl/openssl-3.5.4/LICENSE.txt',
        'libffi-LICENSE.txt':'https://raw.githubusercontent.com/libffi/libffi/v3.4.8/LICENSE',
    }.items():download(url,OUT/filename)
    manifest=dict(sources=sources,python=sys.version.split()[0],openssl=ssl.OPENSSL_VERSION,
                  packages={p:metadata.version(p) for p in ['PySide6_Essentials','shiboken6','PyInstaller']})
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('License collection complete',flush=True)

if __name__=='__main__':main()
