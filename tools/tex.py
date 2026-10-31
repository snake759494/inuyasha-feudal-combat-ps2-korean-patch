"""RW PS2 TXD 텍스처 ↔ RGBA. 업로드 형식(TRXREG·NLOOP)으로 CT32/CT16/원형식 경로를 판별."""
import struct
import numpy as np
import gs4


def info(b, t):
    q = t['dataoff']
    pw, ph = struct.unpack_from('<2I', b, q + 0x20)
    nl = struct.unpack_from('<I', b, q + 0x40)[0] & 0x7fff
    psz = struct.unpack_from('<I', b, t['hdr'] + 0x30)[0]
    return dict(pw=pw, ph=ph, n=nl * 16, pix=q + 0x50, pal=q + psz, ub=nl * 16 * 8 // (pw * ph))


def pal_order(n):
    i = np.arange(n)
    return i if n == 16 else (i & ~0x18) | ((i & 0x08) << 1) | ((i & 0x10) >> 1)


def palette(b, t):
    f = info(b, t)
    n = 16 if t['depth'] == 4 else 256
    p = np.frombuffer(b, np.uint8, n * 4, f['pal'] + 0x50).reshape(n, 4)
    return p[pal_order(n)]


def indices(b, t):
    f = info(b, t); w, h = t['w'], t['h']
    d = b[f['pix']:f['pix'] + f['n']]
    if t['depth'] == 4:
        if f['ub'] == 4:
            a = np.frombuffer(d, np.uint8); return np.stack([a & 15, a >> 4], 1).ravel()[:w * h].reshape(h, w)
        if f['ub'] == 16: return gs4.unswizzle4_16(d, w, h, f['pw'], f['ph'])
        return np.frombuffer(gs4.unswizzle4_w(d, w, h, f['pw']), np.uint8).reshape(h, w)
    if f['ub'] == 8: return np.frombuffer(d, np.uint8)[:w * h].reshape(h, w)
    return np.frombuffer(gs4.unswizzle8_w(d, w, h, f['pw']), np.uint8).reshape(h, w)


def rgba(b, t):
    if t['depth'] == 32:
        f = info(b, t); return np.frombuffer(b, np.uint8, t['w'] * t['h'] * 4, f['pix']).reshape(t['h'], t['w'], 4)
    return palette(b, t)[indices(b, t)]


def encode(b, t, idx):
    """indices → 원래 업로드 형식 바이트 (길이 동일)"""
    f = info(b, t); w, h = t['w'], t['h']
    if t['depth'] == 4:
        if f['ub'] == 4:
            a = idx.ravel().astype(np.uint8); out = (a[0::2] | (a[1::2] << 4)).tobytes()
        elif f['ub'] == 16: out = gs4.swizzle4_16(idx, f['pw'], f['ph'])
        else: out = gs4.swizzle4_w(idx, w, h, f['pw'], f['n'])
    else:
        if f['ub'] == 8: out = idx.astype(np.uint8).tobytes()
        else: out = gs4.swizzle8_w(idx, w, h, f['pw'], f['n'])
    out = out[:f['n']] + b'\0' * (f['n'] - len(out))
    return f['pix'], out
