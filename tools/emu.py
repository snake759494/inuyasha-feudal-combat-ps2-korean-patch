"""테스트 전용: 포터블 PCSX2(work/emu)를 최소화·비활성으로 실행. PINE(28311)으로 가상 패드·상태저장 스크린샷.
가상 패드: 0x10b660 (xori v0,v0,0xffff → 눌림=1) 직후 VPAD 를 OR (포트 0 만).
버튼: SELECT=0x100 START=0x800 U=0x1000 R=0x2000 D=0x4000 L=0x8000 L2=1 R2=2 L1=4 R1=8 T=0x10 O=0x20 X=0x40 S=0x80"""
import subprocess, sys, os, time, glob, zipfile, struct, ctypes, socket
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMU = os.path.join(R, 'work', 'emu'); PIDF = os.path.join(EMU, 'emu.pid'); PORT = 28311
VPAD = 0x000ff000; CAVE = 0x000ff100
BTN = dict(SELECT=0x100, START=0x800, U=0x1000, R=0x2000, D=0x4000, L=0x8000, L2=1, R2=2, L1=4, R1=8, T=0x10, O=0x20, X=0x40, S=0x80)
def j(a): return (2 << 26) | (a >> 2)
def section():
    code = [0x3842ffff,                                  # xori v0,v0,0xffff
            0x16200004,                                  # bnez s1,+4 (포트 0 만)
            0x00000000,
            0x3c010000 | ((VPAD + 0x8000) >> 16),        # lui at
            0x8c210000 | (VPAD & 0xffff),                # lw at
            0x00411025,                                  # or v0,v0,at
            j(0x10b668), 0xae020010]                     # sw v0,0x10(s0)
    out = ['gametitle=Inuyasha Feudal Combat (QA vpad)']
    out += ['patch=1,EE,%08x,word,%08x' % (CAVE + 4 * i, c) for i, c in enumerate(code)]
    out += ['patch=1,EE,0010b660,word,%08x' % j(CAVE), 'patch=1,EE,0010b664,word,00000000']
    return '\n'.join(out) + '\n'
def elf_crc(iso):
    import pycdlib
    i = pycdlib.PyCdlib(); i.open(iso); r = i.get_record(iso_path='/SLUS_211.93;1')
    with open(iso, 'rb') as f: f.seek(r.extent_location() * 2048); d = f.read(r.data_length)
    i.close(); c = 0
    for (x,) in struct.iter_unpack('<I', d[:len(d) // 4 * 4]): c ^= x
    return c
def launch(iso, state=None):
    crc = elf_crc(iso)
    os.makedirs(os.path.join(EMU, 'cheats'), exist_ok=True)
    for f in glob.glob(os.path.join(EMU, 'cheats', '*.pnach')): os.remove(f)
    open(os.path.join(EMU, 'cheats', '%08X.pnach' % crc), 'w').write(section())
    si = subprocess.STARTUPINFO(); si.dwFlags = 1; si.wShowWindow = 7   # SW_SHOWMINNOACTIVE
    args = [os.path.join(EMU, 'pcsx2-qt.exe'), '-batch', '-nogui']
    if state: args += ['-statefile', state]
    p = subprocess.Popen(args + ['--', os.path.abspath(iso)], cwd=EMU, startupinfo=si)
    open(PIDF, 'w').write(str(p.pid)); print('pid', p.pid, 'crc %08X' % crc)
    hide(p.pid)
def hide(pid):
    u = ctypes.windll.user32
    for _ in range(150):
        hs = []
        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def cb(h, l):
            pp = ctypes.c_ulong(); u.GetWindowThreadProcessId(ctypes.c_void_p(h), ctypes.byref(pp))
            if pp.value == pid and u.IsWindowVisible(ctypes.c_void_p(h)): hs.append(h)
            return True
        u.EnumWindows(cb, 0)
        if hs:
            time.sleep(1.0)
            for h in hs: u.ShowWindow(ctypes.c_void_p(h), 7)
            return
        time.sleep(0.2)
def stop():
    if os.path.exists(PIDF):
        subprocess.run(['taskkill', '/F', '/PID', open(PIDF).read().strip()], capture_output=True); os.remove(PIDF)
def pine(payload):
    s = socket.create_connection(('127.0.0.1', PORT), timeout=10)
    s.sendall(struct.pack('<I', len(payload) + 4) + payload)
    def rv(n):
        b = b''
        while len(b) < n:
            c = s.recv(n - len(b))
            if not c: raise EOFError
            b += c
        return b
    n = struct.unpack('<I', rv(4))[0]; body = rv(n - 4); s.close(); return body
def w32(a, v): return pine(struct.pack('<BII', 6, a, v))
def r32(a): return struct.unpack_from('<I', pine(struct.pack('<BI', 2, a)), 1)[0]
def press(names, ms=150):
    m = 0
    for n in names.split('+'): m |= BTN[n]
    w32(VPAD, m); time.sleep(ms / 1000); w32(VPAD, 0); time.sleep(0.15)
def member(p, name):
    import zstandard
    with zipfile.ZipFile(p) as z: i = z.getinfo(name)
    with open(p, 'rb') as f:
        f.seek(i.header_offset); h = f.read(30); n, e = struct.unpack_from('<HH', h, 26); f.seek(n + e, 1)
        raw = f.read(i.compress_size)
    if i.compress_type == 0: return raw
    if i.compress_type == 93: return zstandard.ZstdDecompressor().decompress(raw, max_output_size=i.file_size)
    with zipfile.ZipFile(p) as z: return z.read(name)
def latest():
    ps = glob.glob(os.path.join(EMU, 'sstates', '*.p2s'))
    return max(ps, key=os.path.getmtime) if ps else None
def snap(tag, slot=9):
    old = latest(); t = os.path.getmtime(old) if old else 0
    pine(struct.pack('<BB', 9, slot))
    for _ in range(300):
        p = latest()
        if p and os.path.getmtime(p) > t: time.sleep(1.0); break
        time.sleep(0.1)
    out = os.path.join(R, 'work', 'shots', '%s.png' % tag)
    open(out, 'wb').write(member(p, 'Screenshot.png'))
    if '--ram' in sys.argv: open(os.path.join(R, 'work', 'ram_%s.bin' % tag), 'wb').write(member(p, 'eeMemory.bin'))
    print(out)
if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'launch': launch(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('-') else None)
    elif c == 'stop': stop()
    elif c == 'snap': snap(sys.argv[2])
    elif c == 'press':
        for k in sys.argv[2:]:
            try: time.sleep(float(k))
            except ValueError: press(k)
    elif c == 'save': print(pine(struct.pack('<BB', 9, int(sys.argv[2]))))
    elif c == 'load': print(pine(struct.pack('<BB', 0xa, int(sys.argv[2]))))
