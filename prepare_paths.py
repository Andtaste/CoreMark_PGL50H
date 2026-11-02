from pathlib import Path
import re
root=Path(__file__).resolve().parent
for project in (root/'hardware').iterdir():
    for f in (project/'ipcore').rglob('*'):
        if f.suffix not in {'.v','.idf','.vh','.sv'}: continue
        text=f.read_text(encoding='utf-8')
        def replace(m):
            target=project/'memory'/m.group(1)
            if not target.is_file(): raise FileNotFoundError(target)
            return target.as_posix()
        text=re.sub(r'(?:[A-Za-z]:/[^"<>\n]*?/)?memory/([^"<>\n]+)',replace,text)
        f.write_text(text,encoding='utf-8')
print('RAM initialization paths configured. Open the PDS project and rebuild.')
