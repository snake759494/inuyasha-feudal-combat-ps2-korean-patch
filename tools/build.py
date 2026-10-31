"""한글패치 빌드: 번역 → seq 문자열 교체, 폰트 TXD(512x512, 32열) 재구성, ELF 글리프 함수 패치, ISO 빌드.
인코딩: 2바이트 SJIS형. 리드 0x81~, 트레일 0x40~0x7e·0x80~0xfc (리드당 188자). 글리프 번호 = KBASE + g."""
import os, sys, re, glob, struct, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import fpk, isobuild, seqtext, gs4, txd, tex, imgtext

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ISO = os.path.join(R, 'Inuyasha - Feudal Combat (USA).iso')
OUT_ISO = os.path.join(R, 'Inuyasha - Feudal Combat (USA) (Korean).iso')
TR = os.path.join(R, 'translation')
EXT = os.path.join(R, 'work', 'ext')
FONT = os.path.join(R, 'NanumSquareNeo-dEb.ttf')
KBASE = 96
W = H = 512
ELF_OFF = 0xff000                      # 파일오프셋 = 가상주소 - ELF_OFF

# ---------------------------------------------------------------- 문자표
elf0 = open(os.path.join(EXT, 'SLUS_211.93'), 'rb').read()
_t = elf0[0x232350:0x232350 + 186]
WID = {chr(_t[i]): _t[i + 1] for i in range(0, 186, 2)}
KW = 15


def load_tsv(name):
    out = {}
    for l in open(os.path.join(TR, name), encoding='utf-8'):
        l = l.rstrip('\n')
        if not l or l[0] == '#' or '\t' not in l: continue
        k, v = l.split('\t', 1)
        out[k] = v.replace('\\n', '\n')
    return out


src = {}
for l in open(os.path.join(TR, 'src.tsv'), encoding='utf-8'):
    c = l.rstrip('\n').split('\t')
    src[c[0]] = c[4].replace('\\n', '\n')

ui, story, mission = load_tsv('ko_ui.tsv'), load_tsv('ko_story.tsv'), load_tsv('ko_mission.tsv')


def width(s):
    return sum(KW if ord(ch) > 126 else WID[ch] for ch in s)


# ---------------------------------------------------------------- 능력치 문구 (규칙 번역)
STAT = {'ATK': '공격력', 'DF': '방어력', 'HP': '체력', 'SPD': '속도'}
WHO = {'Player': '플레이어', 'Partner': '파트너'}


def stat_rule(s):
    m = re.fullmatch(r"(Player|Partner)'s (ATK|DF|HP|SPD) increased by (\d+)", s)
    if m: return '%s %s %s 증가' % (WHO[m[1]], STAT[m[2]], m[3])
    m = re.fullmatch(r'LV increased by (\d+)', s)
    if m: return '레벨 %s 증가' % m[1]
    return None


# ---------------------------------------------------------------- 스토리 가운데 정렬
def center_story(en, ko):
    el = en.split('\n')
    ind = [len(x) - len(x.lstrip(' ')) for x in el if x.strip()]
    lines = [x.strip(' ') for x in ko.split('\n')]
    if not ind or min(ind) == 0: return '\n'.join(lines)
    mw = max(width(x) for x in lines)
    n = max(0, round((324 - mw / 2) / 8))
    return '\n'.join(' ' * n + x if x else x for x in lines)


# ---------------------------------------------------------------- 미션 버튼 아이콘 줄 맞춤
def fit_icons(en, ko):
    el, kl = en.split('\n'), ko.split('\n')
    for i, e in enumerate(el):
        if '   ' not in e: continue
        k = kl[i]
        wo = width(e[:e.index('   ')]); kp = k[:k.index('   ')]; wt = width(kp)
        assert wt <= wo + 4, (en, ko, wo, wt)
        n = max(0, round((wo - wt) / 8))
        cut = kp.rfind('(') if '(' in kp else len(kp)
        kl[i] = k[:cut] + ' ' * n + k[cut:]
    return '\n'.join(kl)


# ---------------------------------------------------------------- 엔딩 크레딧 (직함·캐릭터명만, 실존 인물 이름은 원문)
ROLE = {
    'ADAPTATION & RECORDING': '현지화 및 녹음', 'GAME DEVELOPMENT EIGHTING Co., Ltd': '게임 개발 EIGHTING Co., Ltd',
    'PRODUCED BY Bandai Co., Ltd.': '제작 Bandai Co., Ltd.', 'PUBLISHED BY Bandai Games Inc.': '발매 Bandai Games Inc.',
    'Chief Designer': '수석 디자이너', 'Chief Producer': '수석 프로듀서', 'Co-Producer': '공동 프로듀서',
    'Design Integration': '디자인 통합', 'Designers': '디자이너', 'Dialogue Editor': '대사 편집',
    'English Script Adaptation': '영어 대본 각색', 'English Translation': '영어 번역', 'Executive Producer': '총괄 프로듀서',
    'Featuring the Voices of:': '목소리 출연:', 'Integration Advisor': '통합 어드바이저', 'Localization Staff': '현지화 스태프',
    'Main Programmer': '메인 프로그래머', 'Music Composed by': '작곡', 'Produced by': '제작', 'Producer': '프로듀서',
    'Production Assistant': '제작 어시스턴트', 'Production Manager': '제작 매니저', 'Program Integration': '프로그램 통합',
    'Programmers': '프로그래머', 'Project Director': '프로젝트 디렉터', 'Recording Engineers': '녹음 엔지니어',
    'Senior Production Coordinator': '시니어 제작 코디네이터', 'Sound Director': '사운드 디렉터',
    'Sound Engineer': '사운드 엔지니어', 'Supervising Director': '감수 디렉터', 'Video Post-Production': '영상 후반 작업',
    'Voice Director': '음성 디렉터'}
CAST = dict(Inuyasha='이누야샤', Kagome='카고메', Miroku='미로쿠', Sango='산고', Shippo='싯포', Kikyo='키쿄우',
            Sesshomaru='셋쇼마루', Naraku='나라쿠', Kagura='카구라', Koga='코우가', Kohaku='코하쿠', Bankotsu='반코츠')


def credit_line(l):
    t = l.strip(' ')
    if not t: return l
    lead = len(l) - len(l.lstrip(' '))
    if t in ROLE: return ' ' * lead + ROLE[t] + l[lead + len(t):]
    m = re.match(r'( *)(\w+)( +)(.*)$', l)
    if m and m[2] in CAST:
        # 캐릭터명의 오른쪽 끝(픽셀)을 원문과 맞춘다
        right = width(m[1] + m[2]); ko = CAST[m[2]]
        n = max(0, round((right - width(ko)) / 8))
        return ' ' * n + ko + m[3] + m[4]
    return l


trans = {}
for k, en in src.items():
    if '1332' <= k <= '1352':
        nl = '\n'.join(credit_line(x) for x in en.split('\n'))
        if nl != en: trans[k] = nl
        continue
    if k in story: trans[k] = center_story(en, story[k])
    elif k in mission: trans[k] = fit_icons(en, mission[k])
    elif k in ui: trans[k] = ui[k]
    else:
        r = stat_rule(en)
        if r: trans[k] = r

# ---------------------------------------------------------------- 한글 코드 배정
extra = sorted({ch for v in trans.values() for ch in v if ord(ch) > 126})
assert len(extra) <= (W // 16) * (H // 16) - KBASE, len(extra)
CODE = {}
for g, ch in enumerate(extra):
    lead, t = 0x81 + g // 188, g % 188
    t = 0x40 + t + (t >= 0x3f)
    CODE[ch] = bytes([lead, t])
ASC = {ch: ch.encode() for ch in WID}


def enc(s):
    out = b''
    for ch in s:
        if ch == '\n': out += b'\n'
        elif ch in CODE: out += CODE[ch]
        elif ch in ASC: out += ASC[ch]
        else: raise ValueError('문자표에 없음 %r in %r' % (ch, s))
    return out


ENC = {src[k].encode('latin1'): enc(v) for k, v in trans.items()}

# ---------------------------------------------------------------- seq 문자열 교체
stats = dict(inplace=0, moved=0, kept=0)


LETTERS = [b'Time Limit', b'T', b'i', b'm', b'e', b'L', b't']   # chrsel: "Time Limit" 을 한 글자씩 그린다


def patch_letters(d):
    o = d.find(b'\0' * 6 + b'Time Limit\0') + 6
    if o < 6 or o % 16: return
    if [bytes(d[o + 16 * i:o + 16 * i + 16]).split(b'\0')[0] for i in range(7)] != LETTERS: return
    # 겹치지 않는 글자 중 가운데쯤인 'e'(4번째) 자리에 한 줄 전체, 나머지 글자는 공백 (앞 공백은 무시되어 쓸 수 없다)
    word = trans['0450']
    d[o + 64:o + 80] = (enc(word) + b'\0').ljust(16, b'\0')
    for i in (1, 2, 3, 5, 6): d[o + 16 * i:o + 16 * i + 16] = b' '.ljust(16, b'\0')
    stats['letters'] = stats.get('letters', 0) + 1


def patch_seq(d):
    d = bytearray(d)
    patch_letters(d)
    for o, s, sl in seqtext.records(bytes(d), 4):
        if s not in ENC: continue
        if o % 16 and len(s) < 8: continue          # 4 정렬 레코드는 긴 문장만 (짧은 건 스크립트 키일 수 있음)
        new = ENC[s]
        if len(new) + 1 <= sl:
            d[o:o + sl] = new + b'\0' * (sl - len(new)); stats['inplace'] += 1; continue
        refs = [i for i in range(0, len(d) - 3, 4) if struct.unpack_from('<I', d, i)[0] == o]
        if not refs:
            print('  !! 참조 없음·슬롯 초과, 원문 유지:', s[:40]); stats['kept'] += 1; continue
        d += b'\0' * (-len(d) % 16)
        at = len(d); d += new + b'\0'; d += b'\0' * (-len(d) % 16)
        for r in refs: struct.pack_into('<I', d, r, at)
        d[o:o + sl] = b'\0' * sl
        stats['moved'] += 1
    return bytes(d)


# ---------------------------------------------------------------- 폰트
STYLE = {  # 투명, 본체 판정 → 인덱스 함수
    '_b': dict(clear=10),
    '_h': dict(clear=14),
}
_font = ImageFont.truetype(FONT, 13 * 4)


def cov(ch):
    """본체·외곽선 커버리지 (16x16, 0..1)"""
    S = 4
    im = Image.new('L', (16 * S, 16 * S), 0); dr = ImageDraw.Draw(im)
    bb = dr.textbbox((0, 0), ch, font=_font)
    gw, gh = bb[2] - bb[0], bb[3] - bb[1]
    x = (15 * S - gw) / 2 - bb[0]
    y = (1 * S + (14 * S - gh) / 2) - bb[1] if ch != '·' else (16 * S - gh) / 2 - bb[1]
    dr.text((x, y), ch, font=_font, fill=255)
    body = np.asarray(im, np.float32) / 255
    r = 6                                           # 외곽선 1.5px
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    k = (xx * xx + yy * yy) <= r * r + 1
    pad = np.pad(body, r)
    ol = np.zeros_like(body)
    for dy, dx in zip(*np.nonzero(k)):
        ol = np.maximum(ol, pad[dy:dy + body.shape[0], dx:dx + body.shape[1]])
    ds = lambda a: a.reshape(16, S, 16, S).mean((1, 3))
    return ds(body), ds(ol)


def nearest(v, table):
    return min(table, key=lambda t: abs(t[1] - v))[0]


def glyph(ch, style):
    c, o = cov(ch)
    g = np.zeros((16, 16), np.uint8)
    for y in range(16):
        for x in range(16):
            cv, ov = c[y, x], o[y, x]
            if style == '_b':
                if ov < 0.06: v = 10
                elif cv >= 0.85: v = 0
                elif cv > 0.1: v = int(round(9 * (1 - cv)))
                elif ov >= 0.9: v = 9
                else: v = nearest(ov * 128, [(11, 31), (12, 66), (13, 89), (14, 101), (15, 115), (9, 126)])
            else:
                if ov < 0.06: v = 14
                elif cv >= 0.85: v = 15
                elif cv > 0.1: v = min(13, 5 + int(round(cv * 8)))
                elif ov >= 0.9: v = 5
                else: v = nearest(ov * 128, [(0, 10), (1, 31), (2, 65), (3, 94), (4, 116), (5, 126)])
            g[y, x] = v
    return g


_atlas = {}


def atlas(old, style):
    if style in _atlas: return _atlas[style]
    img = np.full((H, W), STYLE[style]['clear'], np.uint8)
    for i in range(128):
        img[i // 32 * 16:i // 32 * 16 + 16, i % 32 * 16:i % 32 * 16 + 16] = old[i // 16 * 16:i // 16 * 16 + 16, i % 16 * 16:i % 16 * 16 + 16]
    for g, ch in enumerate(extra):
        i = KBASE + g
        img[i // 32 * 16:i // 32 * 16 + 16, i % 32 * 16:i % 32 * 16 + 16] = glyph(ch, style)
    _atlas[style] = img
    return img


def patch_txd(b):
    t = txd.textures(b)
    if len(t) != 1 or (t[0]['w'], t[0]['h']) != (256, 128): return None
    style = t[0]['name'][-6:-4]
    if style not in STYLE: return None
    old = gs4.unswizzle4_16(b[0x11c:0x11c + 0x4000], 256, 128, 128, 64)
    img = atlas(old, style)
    pix = gs4.swizzle4_16(img, W // 2, H // 2)
    n = len(pix); delta = n - 0x4000
    out = bytearray(b[:0x11c]) + pix + b[0x11c + 0x4000:]
    for p in (0x4, 0x20, 0x6c, 0xc4): struct.pack_into('<I', out, p, struct.unpack_from('<I', out, p)[0] + delta)
    struct.pack_into('<2I', out, 0x80, W, H)
    lo, hi = struct.unpack_from('<2I', out, 0x90)
    tw, th = int(math.log2(W)), int(math.log2(H))
    lo = (lo & ~((0x3f << 14) | (0xf << 26) | (3 << 30))) | ((W // 64) << 14) | (tw << 26) | ((th & 3) << 30)
    hi = (hi & ~3) | (th >> 2)
    struct.pack_into('<2I', out, 0x90, lo & 0xffffffff, hi)
    struct.pack_into('<I', out, 0x98, n // 256)          # 팔레트 위치(블록 단위) = 픽셀 크기 뒤
    struct.pack_into('<I', out, 0xb0, 0x50 + n)
    pages = (W // 2 // 64) * (H // 2 // 64)
    struct.pack_into('<I', out, 0xb8, pages * 2048 + 0x800)
    struct.pack_into('<2I', out, 0xec, W // 2, H // 2)
    struct.pack_into('<I', out, 0x10c, n // 16)
    return bytes(out)


# ---------------------------------------------------------------- ELF
def asm_patch(elf):
    e = bytearray(elf)
    def w(a, v): struct.pack_into('<I', e, a - ELF_OFF, v)
    def r(a): return struct.unpack_from('<I', e, a - ELF_OFF)[0]
    def lui(a, imm): w(a, (r(a) & 0xffff0000) | imm)
    # 1바이트 경로 UV: 16열 → 32열, 셀 16px / 512
    assert r(0x14f020) == 0x24a4000f, hex(r(0x14f020))
    w(0x14f020, 0x24a4001f)
    w(0x14f030, (r(0x14f030) & ~(0x1f << 6)) | (5 << 6))
    w(0x14f040, (r(0x14f040) & ~(0x1f << 6)) | (5 << 6))
    lui(0x14f034, 0x3d00 if H == 512 else 0x3d80)
    lui(0x14f058, 0x3d00)
    lui(0x14f068, 0x3d00)
    lui(0x14f07c, 0x3d00 if H == 512 else 0x3d80)
    # 2바이트 경로 0x14ee98~0x14ef54 를 한글 글리프 계산으로 교체
    j = lambda a: (2 << 26) | (a >> 2)
    code = [
        0x92420000,             # lbu v0,0(s2)
        0x92430001,             # lbu v1,1(s2)
        0x2442ff7f,             # addiu v0,v0,-0x81
        0x240400bc,             # addiu a0,zero,188
        0x00440018,             # mult v0,a0
        0x00001012,             # mflo v0
        0x2c640080,             # sltiu a0,v1,0x80
        0x38840001,             # xori a0,a0,1
        0x00641823,             # subu v1,v1,a0
        0x2463ffc0,             # addiu v1,v1,-0x40
        0x00431021,             # addu v0,v0,v1
        0x24420000 | KBASE,     # addiu v0,v0,KBASE
        0xafa20000,             # sw v0,0(sp)
        0x3c014170,             # lui at,0x4170 (15.0)
        0x44810000,             # mtc1 at,f0
        0x3c014180,             # lui at,0x4180 (16.0)
        0x44810800,             # mtc1 at,f1
        0xe6000000,             # swc1 f0,0(s0)
        0xe6010004,             # swc1 f1,4(s0)
        0xae000008,             # sw zero,8(s0)
        0x26490002,             # addiu t1,s2,2
        0x326a0002,             # andi t2,s3,2
        0x3c030002,             # lui v1,2
        0x34630100,             # ori v1,v1,0x100
        0x24060191,             # addiu a2,zero,0x191
        0x2404000b,             # addiu a0,zero,0xb
        0x3c050045,             # lui a1,0x45
        0x8ca2b168,             # lw v0,-0x4e98(a1)
        0x00431024,             # and v0,v0,v1
        j(0x14eff4),            # j 0x14eff4
        0x0082300b,             # movn a2,a0,v0
    ]
    for i, c in enumerate(code): w(0x14ee98 + 4 * i, c)
    for a in range(0x14ee98 + 4 * len(code), 0x14ef58, 4): w(a, 0)
    return bytes(e)


# ---------------------------------------------------------------- 이미지 글자
img_count = [0]


def patch_img(nm, b):
    out = None
    for t in txd.textures(b):
        k = imgtext.key_of(nm, t['name'])
        if k not in imgtext.IMG: continue
        idx, _ = imgtext.render(b, t, imgtext.IMG[k])
        if out is None: out = bytearray(b)
        p, data = tex.encode(b, t, idx)
        out[p:p + len(data)] = data
        img_count[0] += 1
    return bytes(out) if out else None


# ---------------------------------------------------------------- 메인
def main():
    files = {}
    for f in sorted(glob.glob(os.path.join(EXT, 'FPACK', '**', '*.FPK'), recursive=True)):
        d = open(f, 'rb').read()
        rep = {}
        for nm, data in fpk.unpack(d):
            if nm.endswith('.seq'):
                nd = patch_seq(data)
                if nd != data: rep[nm] = nd
            elif nm.startswith('font/') and nm.endswith('.txd') and len(data) > 0x200:
                nd = patch_txd(data)
                if nd: rep[nm] = nd
            elif nm.endswith('.txd') and len(data) > 0x200:
                nd = patch_img(nm, data)
                if nd: rep[nm] = nd
        if rep:
            iso = '/' + os.path.relpath(f, EXT).replace(os.sep, '/')
            files[iso] = fpk.repack(d, rep)
            print(iso, len(rep))
    files['/SLUS_211.93'] = asm_patch(elf0)
    print('문자열', stats, '한글', len(extra), '이미지', img_count[0])
    isobuild.build(SRC_ISO, OUT_ISO, files)
    print('완료', OUT_ISO)


if __name__ == '__main__':
    main()
