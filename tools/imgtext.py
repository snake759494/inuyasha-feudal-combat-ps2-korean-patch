"""이미지 속 영어 글자 → 한글. 원본에서 채움(세로 그라데이션)·외곽선 색을 뽑아 같은 자리에 다시 그리고
원래 팔레트로 양자화한다(팔레트·크기 불변). 사진 위 글자(스테이지 이름)는 지운 뒤(inpaint) 다시 쓴다."""
import os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import tex

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E = os.path.join(R, 'NanumSquareNeo-eHv.ttf')        # 굵은 고딕 (대부분의 로고형 글자)
S = os.path.join(R, 'SeoulHangangEB.ttf')            # 명조 계열 (세리프 원문)
G = os.path.join(R, 'work', 'fonts', 'Galmuri11-Bold.ttf')   # 아주 작은 글자 전용

NAME = dict(Bnk='반코츠', Bkt='반코츠', Ban='반코츠', Inu='이누야샤', Kga='코우가', Kgm='카고메', Kgr='카구라',
            Khk='코하쿠', Kky='키쿄우', Mrk='미로쿠', Nrk='나라쿠', Ses='셋쇼마루', Ssm='셋쇼마루', Sng='산고',
            Spo='싯포', Shp='싯포', Sip='싯포', Nin='인간 이누야샤', Yin='요괴 이누야샤')
STAGE = ['초원', '신비의 숲', '흑진주', '바위 지대', '고찰', '저택 폐허', '나라쿠의 성']


def names(prefix, keys, font=E, two=False):
    out = {}
    for k in keys:
        t = NAME[k]
        if two and ' ' in t: t = t.replace(' ', '\n')
        out[prefix + k] = dict(text=t, font=font)
    return out


IMG = {
    '5400/NowLoading': dict(text='로딩 중...', font=E),
    '5000/SpiritPower': dict(text='영력', font=G),
    '5000/Time': dict(text='시간', font=E),
    '5500/Ren': dict(text='히트', font=E),
    '5505/Shousha': dict(text='승자', font=S),
    '5506/Continue': dict(text='계속할까요?', font=E),
    '5506/Hai': dict(text='예', font=S),
    '5506/Iie': dict(text='아니오', font=S),
    '5506/Kan': dict(text='게임\n오버', font=S),
    '5508/M_S_Moji02': dict(text='미션 실패!', font=E),
    '5509/M_S_Moji01': dict(text='미션 성공!', font=E),
    '5511/Senme': dict(text='라운드', font=E),
    '5512/aishou01': dict(text='궁합 레벨 업', font=E),
    '5512/aishou02': dict(text='궁합 레벨 다운', font=E),
    '5512/aishou03': dict(text='최고', font=E),
    '5512/aishou04': dict(text='좋음', font=E),
    '5512/aishou05': dict(text='보통', font=E),
    '5512/aishou06': dict(text='나쁨', font=E),
    '5110/ModeSelect': dict(text='모드 선택', font=E),
    '5110/Option': dict(text='옵션', font=E),
    '5110/Mj_Story': dict(text='스토리 모드', font=E),
    '5110/Mj_Misson': dict(text='미션 모드', font=E),
    '5110/Mj_Battle': dict(text='대전 모드', font=E),
    '5110/Mj_Practice': dict(text='연습 모드', font=E),
    '5110/Mj_Option': dict(text='옵션', font=E),
    '5110/Mj_Omake': dict(text='보너스', font=E),
    '5110/Mj_Game': dict(text='게임', font=E),
    '5110/Mj_Sound': dict(text='사운드 설정', font=E),
    '5110/Mj_Memory': dict(text='세이브·로드', font=E),
    '5110/Mj_Controller': dict(text='컨트롤러 설정', font=E),
    '5110/Mj_Default': dict(text='초기 설정', font=E),
    '5110/Mj_Back_Ms': dict(text='모드 선택으로', font=E),
    '5110/Mj_Title': dict(text='타이틀 화면으로', font=E),
    '5130/Story': dict(text='스토리 모드', font=E),
    '5130/Story_Inu': dict(text='이누야샤 편', font=S),
    '5130/Story_Mr_Sn': dict(text='미로쿠·산고 편', font=S),
    '5130/Story_Mrk': dict(text='미로쿠·산고 편', font=S),
    '5130/Story_Ssm': dict(text='셋쇼마루 편', font=S),
    '5130/Story_Nrk': dict(text='나라쿠 편', font=S),
    '5130/Story_Shp': dict(text='싯포 편', font=S),
    '5200/C_Select': dict(text='캐릭터 선택', font=E),
    '5200/St_Select': dict(text='스테이지 선택', font=E),
    '5200/Kumiawase': dict(text='대전 방식 선택', font=S),
    '5200/T_Settei': dict(text='대전\n설정', font=S),
    '5200/Partner': dict(text='파트너', font=E),
    '5200/Player': dict(text='플레이어', font=E),
    '5301/Data': dict(text='데이터', font=S),
    '5301/Funaka': dict(text='나쁨', font=E),
    '5301/Futuu': dict(text='보통', font=E),
    '5301/Yuko': dict(text='좋음', font=E),
    '5301/PlayerStatus': dict(text='스테이터스 화면', font=E),
    '5301/Saisho': dict(text='처음부터', font=E),
    '5700/Start': dict(text='START 버튼을 누르세요', font=E),
    '5300/Lv_Select01': dict(text='레벨 선택', font=S),
    '5300/N_S_S': dict(text='마지막 미션', font=E),
    '5300/Sumi': dict(text='완료', font=E, k=0),
    '5300/Pt_Waku': dict(text='파트너', font=E, region=(80, 8, 192, 34), bgcol=200),
    '5900/Story_Inu': dict(text='이누야샤 편', font=S),
    '5900/Story_Ssm': dict(text='셋쇼마루 편', font=S),
    '5900/Story_Mrk': dict(text='미로쿠·산고 편', font=S),
    '5900/Story_Spo': dict(text='싯포 편', font=S),
    '5900/Story_Last': dict(text='최종장', font=S),
}
for i in range(1, 8): IMG['5900/Story_%02d' % i] = dict(text='제%d화' % i, font=S)
for a, b in (('Hajime', '시작!'), ('Shoubu', '승부!')):
    for i in range(1, 5): IMG['5501/%s%02d' % (a, i)] = dict(text=b, font=E, hull=True, blur=i >= 3)
for k, t in (('5503/J_kire', '타임 업'), ('5504/Aiuchi', '무승부'), ('5510/S_ryo', '끝')):
    IMG[k + '01'] = dict(text=t, font=E); IMG[k + '02'] = dict(text=t, font=E, blur=True)
for i, s in enumerate(STAGE):
    IMG['5200/Cs_St%02d' % (i + 1)] = dict(text=s, font=S, photo=True, size=17)
    IMG['5300/Bg_Sam%02d' % (i + 1)] = dict(text=s, font=S, photo=True, size=24)
IMG.update(names('5000/Pl_Name_', ['Inu', 'Kgm'], G))
IMG.update(names('5010/Pl_Name_', ['Ban', 'Inu', 'Kga', 'Kgm', 'Kgr', 'Khk', 'Kky', 'Mrk', 'Nrk', 'Ses', 'Sng', 'Spo'], G))
IMG.update(names('5505/Win_', ['Bnk', 'Inu', 'Kga', 'Kgm', 'Kgr', 'Khk', 'Kky', 'Mrk', 'Nin', 'Nrk', 'Ses', 'Sng', 'Spo', 'Yin'], two=True))
IMG.update(names('5200/N_', ['Bkt', 'Inu', 'Kga', 'Kgm', 'Kgr', 'Khk', 'Kky', 'Mrk', 'Nin', 'Nrk', 'Sng', 'Shp', 'Ses', 'Yin'], two=True))
IMG.update(names('5301/St_', ['Bnk', 'Inu', 'Kga', 'Kgm', 'Kgr', 'Khk', 'Kky', 'Mrk', 'Nrk', 'Ses', 'Sip', 'Sng', 'Nin', 'Yin']))
IMG.update(names('5300/Pt_N_', ['Kgm', 'Inu', 'Sng', 'Mrk', 'Kky', 'Spo', 'Kgr', 'Ssm', 'Nrk', 'Khk', 'Bnk', 'Kga', 'Nin', 'Yin'], two=True))


# ---------------------------------------------------------------- 렌더
def text_mask(text, font, box_w, box_h, ss=4):
    """여러 줄 글자 알파(0..1). box 에 맞추되 가로가 넘치면 가로만 줄인다."""
    lines = text.split('\n')
    if font == G:
        f = ImageFont.truetype(G, 12); ss = 1
    else:
        f = ImageFont.truetype(font, int(box_h * ss / len(lines) * 1.0))
    ims = []
    for ln in lines:
        bb = f.getbbox(ln)
        im = Image.new('L', (bb[2] - bb[0] + 2, bb[3] - bb[1] + 2), 0)
        ImageDraw.Draw(im).text((1 - bb[0], 1 - bb[1]), ln, font=f, fill=255)
        ims.append(im)
    lh = max(i.height for i in ims); gap = int(lh * 0.22) if len(lines) > 1 else 0
    W = max(i.width for i in ims); Ht = lh * len(lines) + gap * (len(lines) - 1)
    big = Image.new('L', (W, Ht), 0)
    for k, im in enumerate(ims): big.paste(im, ((W - im.width) // 2, k * (lh + gap) + (lh - im.height) // 2))
    if font == G:
        return np.asarray(big, np.float32) / 255
    sc = min(box_h / (Ht / ss), 1e9) / ss
    w, h = max(1, round(W * sc)), max(1, round(Ht * sc))
    if w > box_w: w = box_w
    return np.asarray(big.resize((w, h), Image.LANCZOS), np.float32) / 255


def dilate(a, r):
    if r <= 0: return a
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    return cv2.dilate(a, k)


def style(rgba):
    a = rgba[..., 3]
    m = (a >= 100).astype(np.uint8)
    d = cv2.distanceTransform(m, cv2.DIST_L2, 3)
    ys, xs = np.nonzero(a > 16)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    h = y1 - y0
    k = max(1, int(round(h * 0.07)))
    ring = (d > 0) & (d <= k)
    inner = d > k + 0.5
    if inner.sum() < 10: inner = d > 1
    oc = np.median(rgba[ring][:, :3], 0) if ring.any() else np.array([0, 0, 0])
    far = (np.abs(rgba[..., :3] - oc).sum(2) > 150) & (a >= 100)
    if far.sum() > max(10, inner.sum() * 0.3): inner = far & ((d > k * 0.5) | (k <= 1))
    rows = []
    for y in range(y0, y1):
        sel = inner[y]
        rows.append(np.median(rgba[y][sel][:, :3], 0) if sel.sum() >= 2 else None)
    good = [r for r in rows if r is not None]
    if not good: good = [np.array([255, 255, 255])]
    filled, last = [], good[0]
    for r in rows:
        last = r if r is not None else last; filled.append(last)
    return dict(box=(x0, y0, x1, y1), k=k, outline=oc, grad=np.array(filled, np.float32))


def compose(shape, st, spec):
    Hh, Ww = shape
    x0, y0, x1, y1 = st['box']; k = st['k']
    bw, bh = x1 - x0, y1 - y0
    small = spec['font'] == G
    if small: k = 1
    if 'k' in spec: k = spec['k']
    tm = text_mask(spec['text'], spec['font'], max(4, min(Ww - 2 * k - 2, max(bw, int(bw * 1.15))) - 2 * k), max(4, bh - 2 * k) if not spec.get('photo') else bh)
    th, tw = tm.shape
    if tw > Ww - 2 * k: tm = cv2.resize(tm, (Ww - 2 * k, th)); tw = tm.shape[1]
    cx = (x0 + x1) / 2 if not spec.get('left') else x0 + k + tw / 2
    if spec.get('right'): cx = spec['right'] - k - tw / 2
    ox = int(round(min(max(cx - tw / 2, k), Ww - k - tw))); oy = int(round(min(max((y0 + y1) / 2 - th / 2, k), Hh - k - th)))
    body = np.zeros((Hh, Ww), np.float32); body[oy:oy + th, ox:ox + tw] = tm
    if small: body = (body > 0.5).astype(np.float32)
    ol = dilate(body, k)
    if not small: ol = cv2.GaussianBlur(ol, (3, 3), 0.6)
    ol = np.maximum(ol, body)
    g = st['grad']
    yy = np.clip(((np.arange(Hh) - oy) / max(1, th - 1) * (len(g) - 1)).round().astype(int), 0, len(g) - 1)
    fill = g[yy][:, None, :].repeat(Ww, 1)
    col = fill * body[..., None] + st['outline'][None, None, :] * (1 - body[..., None])
    return np.dstack([col, ol * 255]).astype(np.float32)


def quantize(rgba, pal):
    """rgba(알파 0..255) → 팔레트 인덱스 (팔레트 알파 0..128)"""
    p = pal.astype(np.float32).copy(); p[:, 3] = np.minimum(255, p[:, 3] * 2)
    px = rgba.reshape(-1, 4).astype(np.float32)
    w = np.array([1, 1, 1, 3], np.float32)
    pa = p[:, 3:4] / 255; xa = px[:, 3:4] / 255
    # 미리 곱한 색으로 비교 → 투명 근처에서 색 차이 무시
    d = (((px[:, None, :3] * xa[:, None] - p[None, :, :3] * pa[None]) ** 2).sum(2) + w[3] * (px[:, None, 3] - p[None, :, 3]) ** 2)
    return d.argmin(1).astype(np.uint8).reshape(rgba.shape[:2])


def hull_mask(a):
    ys, xs = np.nonzero(a > 8)
    m = np.zeros(a.shape, np.uint8)
    if len(xs) < 3: return m.astype(np.float32)
    pts = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))
    cv2.fillConvexPoly(m, pts, 1)
    return dilate(m.astype(np.float32), 2)


def render(b, t, spec, ref=None):
    """ref: blur/hull 조각용 기준(선명한 원본 RGBA)"""
    pal = tex.palette(b, t)
    src = tex.rgba(b, t).astype(np.float32); src[..., 3] = np.minimum(255, src[..., 3] * 2)
    H, W = src.shape[:2]
    if spec.get('photo'): return photo(src, pal, spec)
    if 'region' in spec:
        x0, y0, x1, y1 = spec['region']
        sub = src[y0:y1, x0:x1].copy()
        st = style(sub)
        new = compose(sub.shape[:2], st, spec)
        out = src.copy()
        if 'bgcol' in spec:
            base = out[y0:y1, spec['bgcol']][:, None, :].repeat(x1 - x0, 1)
            na = new[..., 3:4] / 255
            out[y0:y1, x0:x1, :3] = base[..., :3] * (1 - na) + new[..., :3] * na
            out[y0:y1, x0:x1, 3] = np.maximum(base[..., 3], new[..., 3])
        else:
            out[y0:y1, x0:x1] = new
        # 영역 밖에 걸친 원본 장식(선)은 원래대로: 영역 안 원본 중 글자 아닌 부분은 버림
        return quantize(out, pal), out
    st = style(ref if ref is not None else src)
    new = compose((H, W), st, spec)
    if spec.get('blur'):
        a = cv2.GaussianBlur(new[..., 3], (0, 0), max(2, (st['box'][3] - st['box'][1]) / 14))
        sel = src[..., 3] > 30
        c = np.median(src[sel][:, :3], 0) if sel.any() else np.array([255, 160, 0])
        mx = src[..., 3].max()
        new = np.dstack([np.broadcast_to(c, (H, W, 3)), a / max(a.max(), 1) * mx]).astype(np.float32)
    if spec.get('hull'):
        new[..., 3] *= hull_mask(src[..., 3])
    return quantize(new, pal), new


def photo(src, pal, spec):
    img = src[..., :3].astype(np.uint8).copy()
    H, W = img.shape[:2]
    white = (img.min(2) > 150).astype(np.uint8)
    dark = (img.max(2) < 90).astype(np.uint8)
    tl = white & cv2.dilate(dark, np.ones((5, 5), np.uint8)) & (src[..., 3] > 100)
    tl[:int(H * (0.55 if W <= H else 0.3))] = 0
    n, lab, stt, _ = cv2.connectedComponentsWithStats(tl)
    keep = np.zeros_like(tl)
    for i in range(1, n):
        x, y, w, h, a = stt[i]
        if h <= H * 0.2 and w <= W * 0.25 and a >= 3 and (h >= 5 or w <= 4): keep[lab == i] = 1
    ys, xs = np.nonzero(keep)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    m = cv2.dilate(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    opaque = (src[..., 3] > 100).astype(np.uint8)
    m &= opaque
    clean = cv2.inpaint(img, (m | (1 - opaque)) * 255, 5, cv2.INPAINT_TELEA)
    th = spec.get('size', 15)
    up = 3 if W > H else 0
    st = dict(box=(x0, y1 - th - up, x1, y1 - up), k=2, outline=np.array([20, 16, 12], np.float32),
              grad=np.array([[250, 248, 240], [230, 226, 215]], np.float32))
    new = compose((H, W), st, dict(spec, right=x1))
    a = new[..., 3:4] / 255
    out = src.copy(); out[..., :3] = clean * (1 - a) + new[..., :3] * a
    out[..., 3] = np.maximum(out[..., 3], new[..., 3] * (src[..., 3].max() / 255 > 0))
    return quantize(out, pal), out


def key_of(txdpath, name):
    return os.path.basename(txdpath).split('_')[0] + '/' + name.rsplit('.', 1)[0]
