"""원본 ISO 의 FPACK/ 과 실행파일을 work/ext 로 꺼낸다 (build.py 입력). 사용: python tools/unpack_iso.py"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import isobuild
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(R, 'Inuyasha - Feudal Combat (USA).iso')
EXT = os.path.join(R, 'work', 'ext')

with open(SRC, 'rb') as f:
    n = 0
    for path, (lba, size, _) in sorted(isobuild.records(f).items()):
        if not (path.startswith('/FPACK/') or path == '/SLUS_211.93'): continue
        out = os.path.join(EXT, *path.strip('/').split('/'))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        f.seek(lba * isobuild.SEC)
        open(out, 'wb').write(f.read(size)); n += 1
print(n, 'files ->', EXT)
