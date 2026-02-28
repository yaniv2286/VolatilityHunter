import glob, re, subprocess, os
from pathlib import Path

zulu_home = Path(os.environ.get('USERPROFILE', r'C:\Users\Public')) / 'zulu-jre17'
candidates = [
    str(zulu_home / 'bin' / 'javaw.exe'),
    r'C:\Program Files\thinkorswim\jre\bin\javaw.exe',
]
for c in candidates:
    p = Path(c)
    if not p.is_file():
        print(f'MISSING: {c}')
        continue
    try:
        out = subprocess.check_output([str(p), '-version'], stderr=subprocess.STDOUT, timeout=5).decode(errors='ignore')
        m = re.search(r'version "(\d+)(?:\.(\d+))?', out)
        if m:
            major = int(m.group(1))
            if major == 1:
                major = int(m.group(2) or 0)
            verdict = 'ACCEPTED' if major >= 17 else 'REJECTED (< 17)'
            print(f'Java {major}: {p} --> {verdict}')
    except Exception as e:
        print(f'ERROR {c}: {e}')
