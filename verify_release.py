# Author: Kerwin
"""Public documentation, author, notices, data paths and about-page regressions."""
import os,sys,re,tempfile,subprocess
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parent
from app_info import AUTHOR,EMAIL,VERSION,REPOSITORY
assert AUTHOR=='kerwin' and EMAIL=='kerwin126@foxmail.com'
assert VERSION in (ROOT/'version_info.txt').read_text(encoding='utf-8')
readme=(ROOT/'README.md').read_text(encoding='utf-8')
assert 'Better lyrics | 浮词' in readme and '@ KUST (Kunming University of Science and Technology)' in readme and REPOSITORY in readme
for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',readme):
    assert (ROOT/target).is_file(),('missing screenshot',target)
for name in ['LICENSE','THIRD_PARTY_NOTICES.md','docs/DEPLOYMENT.md','docs/PRIVACY.md']:
    assert (ROOT/name).is_file()
for name in ['LGPL-3.0-only.txt','GPL-3.0-only.txt','Python-LICENSE.txt','Microsoft-VC-Runtime-LICENSE.txt','Inno-Setup-LICENSE.txt','manifest.json']:
    assert (ROOT/'third_party/licenses'/name).is_file(),name
with tempfile.TemporaryDirectory() as folder:
    root=Path(folder);install=root/'Install 中文';install.mkdir()
    (install/'installed.flag').write_text('installed')
    code='import sys,json;from pathlib import Path;sys.frozen=True;sys.executable='+repr(str(install/'浮词.exe'))+';import app_paths;print(json.dumps([str(app_paths.APP_DIR),str(app_paths.DATA_DIR)]))'
    env=dict(os.environ,LOCALAPPDATA=str(root/'Profile'),PYTHONPATH=str(ROOT))
    import json
    result=json.loads(subprocess.check_output([sys.executable,'-c',code],env=env,encoding='utf-8'))
    assert Path(result[0])==install and Path(result[1])==root/'Profile/BetterLyrics'

from PySide6.QtWidgets import QApplication,QLabel,QPushButton
from about_page import build_about_page
app=QApplication.instance() or QApplication([])
page=build_about_page(None)
text=' '.join(item.text() for item in page.findChildren(QLabel))
for expected in [AUTHOR,EMAIL,'@ KUST (Kunming University of Science and Technology)',VERSION,'LGPL','非商业']:assert expected in text,expected
assert {'GitHub 仓库','反馈问题','联系作者','部署教程','项目许可','第三方许可'}<={b.text() for b in page.findChildren(QPushButton)}
page.close()
print('PASS: public author/contact/version; all README screenshots; license corpus; installed per-user data directory; about content and document actions')
