"""원본 ISO 를 복사한 뒤 바뀐 파일만 써 넣는다.
원래 섹터에 들어가면 제자리, 아니면 DUMMY.DAT 앞 빈 영역(295405~600000)에 놓고
ISO9660 디렉터리 레코드와 UDF File Entry 를 함께 고친다."""
import os, shutil, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import udf

SEC = 2048
FREE_START = 296000          # 마지막 파일 끝(295405) 이후
FREE_END = 600000            # DUMMY.DAT


def records(f):
    """{'/DIR/NAME': (lba, size, 레코드 파일오프셋)} — ISO9660 전체 트리"""
    f.seek(16 * SEC); pvd = f.read(SEC)
    out = {}

    def walk(lba, size, path):
        f.seek(lba * SEC); d = f.read(size); p = 0
        while p < len(d):
            n = d[p]
            if n == 0:
                p = (p // SEC + 1) * SEC; continue
            el, sz = struct.unpack_from('<I', d, p + 2)[0], struct.unpack_from('<I', d, p + 10)[0]
            nm = d[p + 33:p + 33 + d[p + 32]].decode('latin1').split(';')[0]
            if nm not in ('\x00', '\x01'):
                full = path + '/' + nm
                if d[p + 25] & 2: walk(el, sz, full)
                else: out[full.upper()] = (el, sz, lba * SEC + p)
            p += n
    rl, rs = struct.unpack_from('<I', pvd, 156 + 2)[0], struct.unpack_from('<I', pvd, 156 + 10)[0]
    walk(rl, rs, '')
    return out


def both32(v):
    return struct.pack('<I', v) + struct.pack('>I', v)


def build(src, dst, files):
    """files: {'/FPACK/GAME/1000.FPK': bytes}"""
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
        shutil.copyfile(src, dst)
    with open(src, 'rb') as s:
        orig = records(s)
    nxt = FREE_START
    with open(dst, 'r+b') as f:
        u = udf.UDF(f)
        # 이전 빌드 흔적: 원본 레코드로 되돌린 뒤 다시 쓴다
        for path, (lba, size, rec) in orig.items():
            f.seek(rec + 2); cur = struct.unpack('<I', f.read(4))[0]
            if cur != lba:
                f.seek(rec + 2); f.write(both32(lba)); f.write(both32(size))
                u.set_file(path, lba, size)
                with open(src, 'rb') as s:
                    s.seek(lba * SEC); data = s.read((size + SEC - 1) // SEC * SEC)
                f.seek(lba * SEC); f.write(data)
        for path, data in files.items():
            lba, size, rec = orig[path.upper()]
            cap = (size + SEC - 1) // SEC
            need = (len(data) + SEC - 1) // SEC
            if need <= cap:
                at = lba
            else:
                at = nxt; nxt += need + 16
                assert nxt < FREE_END
            f.seek(at * SEC); f.write(data + b'\0' * (need * SEC - len(data)))
            f.seek(rec + 2); f.write(both32(at)); f.write(both32(len(data)))
            u.set_file(path, at, len(data))
        # 빈 영역의 이전 빌드 찌꺼기 지우기 (xdelta 크기 절약)
        f.seek(nxt * SEC)
        z = b'\0' * (SEC * 1024)
        pos = nxt
        while pos < FREE_END:
            n = min(1024, FREE_END - pos)
            f.write(z[:n * SEC]); pos += n
