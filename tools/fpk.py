"""FPK 아카이브: 헤더 [u32 ?][u32 개수][u32 0x10][u32 파일크기], 항목 0x30 = 이름 0x20, u32 0, 오프셋, 압축크기, 원크기.
압축은 ELF 0x113a20 의 LZ (비트 MSB 우선, 1=리터럴). 압축크기==원크기면 무압축."""
import struct

def parse(d):
    cnt = struct.unpack_from('<I', d, 4)[0]
    out = []
    for i in range(cnt):
        b = 0x10 + i * 0x30
        nm = d[b:b + 0x20].split(b'\0')[0].decode()
        z, off, cs, ds = struct.unpack_from('<4I', d, b + 0x20)
        out.append((nm, off, cs, ds))
    return out

def decompress(src, ds):
    out = bytearray(); p = 0; reg = 0x8000
    def bit():
        nonlocal p, reg
        if reg == 0x8000:
            reg = (src[p] << 8) | 0x80; p += 1
        b = reg & 0x8000; reg = (reg << 1) & 0xffff
        return 1 if b else 0
    while True:
        if bit():
            out.append(src[p]); p += 1; continue
        if bit():
            v = (src[p] << 8) | src[p + 1]; p += 2
            n = v & 7; off = (v >> 3) - 0x2000
            if n: n += 2
            else:
                n = src[p]; p += 1
                if n == 0: break
                n += 1
        else:
            n = bit() * 2; n += bit(); n += 2
            off = src[p] - 0x100; p += 1
        s = len(out) + off
        for k in range(n): out.append(out[s + k])
    return bytes(out)

def unpack(d):
    for nm, off, cs, ds in parse(d):
        raw = d[off:off + cs]
        yield nm, (raw if cs == ds else decompress(raw, ds))

def compress(data):
    """탐욕 LZ. 해시 체인으로 최장 일치(창 8191, 길이 2..256)."""
    out = bytearray(); bits = []; pend = bytearray()
    flagpos = None; nb = 0
    def putbit(b):
        nonlocal flagpos, nb
        if nb == 0:
            flagpos = len(out); out.append(0)
        if b: out[flagpos] |= 0x80 >> nb
        nb = (nb + 1) & 7
    n = len(data); i = 0; heads = {}
    def ins(j):
        if j + 2 <= n:
            heads.setdefault(data[j:j + 2], []).append(j)
    while i < n:
        bl = 0; bo = 0
        cand = heads.get(data[i:i + 2]) if i + 2 <= n else None
        if cand:
            lim = min(256, n - i)
            for j in reversed(cand[-64:]):
                if i - j > 8191: break
                l = 2
                while l < lim and data[j + l] == data[i + l]: l += 1
                if l > bl: bl, bo = l, i - j
                if l == lim: break
        if bl >= 3 or (bl == 2 and bo <= 256):
            if bl <= 5 and bo <= 256:
                putbit(0); putbit(0); x = bl - 2
                putbit(x >> 1); putbit(x & 1); out.append(0x100 - bo)
            elif bl <= 9:
                putbit(0); putbit(1); v = ((0x2000 - bo) << 3) | (bl - 2)
                out += bytes([v >> 8, v & 0xff])
            else:
                putbit(0); putbit(1); v = ((0x2000 - bo) << 3)
                out += bytes([v >> 8, v & 0xff, bl - 1])
            for k in range(bl): ins(i + k)
            i += bl
        else:
            putbit(1); out.append(data[i]); ins(i); i += 1
    putbit(0); putbit(1); out += b'\0\0\0'
    return bytes(out)

def build(entries, hdr0):
    """entries: [(이름, 데이터)] → FPK 바이트. 압축이 이득 없으면 무압축 저장."""
    cnt = len(entries)
    pos = 0x10 + cnt * 0x30
    pos = (pos + 15) & ~15
    tab = bytearray(); body = bytearray()
    for nm, data in entries:
        c = compress(data)
        if len(c) >= len(data): c = data
        off = pos + len(body)
        tab += nm.encode().ljust(0x20, b'\0') + struct.pack('<4I', 0, off, len(c), len(data))
        body += c
        body += b'\0' * ((-len(body)) % 16)
    head = struct.pack('<4I', hdr0, cnt, 0x10, 0) + tab
    head += b'\0' * (pos - len(head))
    d = bytearray(head + body)
    struct.pack_into('<I', d, 12, len(d))
    return bytes(d)

def repack(d, repl):
    """원본 FPK 바이트 d 에서 repl {이름: 원본데이터} 만 다시 압축해 넣고 나머지는 원래 압축본 그대로"""
    hdr0 = struct.unpack_from('<I', d, 0)[0]
    ents = parse(d)
    cnt = len(ents)
    pos = (0x10 + cnt * 0x30 + 15) & ~15
    tab = bytearray(); body = bytearray()
    for nm, off, cs, ds in ents:
        if nm in repl:
            data = repl[nm]; c = compress(data)
            if len(c) >= len(data): c = data
            raw, ds = c, len(data)
        else:
            raw = d[off:off + cs]
        o = pos + len(body)
        tab += nm.encode().ljust(0x20, b'\0') + struct.pack('<4I', 0, o, len(raw), ds)
        body += raw
        body += b'\0' * ((-len(body)) % 16)
    missing = set(repl) - {e[0] for e in ents}
    assert not missing, missing
    head = struct.pack('<4I', hdr0, cnt, 0x10, 0) + tab
    head += b'\0' * (pos - len(head))
    out = bytearray(head + body)
    struct.pack_into('<I', out, 12, len(out))
    return bytes(out)
