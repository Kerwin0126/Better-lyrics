# Author: Kerwin
"""Keep the Windows version resource in sync with app_info.VERSION."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app_info import VERSION
parts=tuple(int(x) for x in VERSION.split('.'))+(0,)
target=ROOT/'version_info.txt'
text=target.read_text(encoding='utf-8')
import re
text=re.sub(r'filevers=\([^)]*\), prodvers=\([^)]*\)',f'filevers={parts}, prodvers={parts}',text)
text=re.sub(r"(StringStruct\('(?:FileVersion|ProductVersion)', ')[^']+",lambda m:m[1]+VERSION,text)
target.write_text(text,encoding='utf-8')
print(VERSION)
