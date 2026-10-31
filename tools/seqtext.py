"""seq 스크립트 안의 문자열 레코드 찾기. 레코드는 16바이트 정렬 시작, NUL 종료, 16바이트 단위 0 패딩."""
import re
PAT = re.compile(rb'[\x0a\x20-\x7e]{2,}\x00')
SKIP = re.compile(r'(^[a-z0-9_]+(/[a-z0-9_.]+)+$|\.seq|\.txd|\.dff|\.fpk|==|=$|^[A-Z0-9_]+=|(?<!to )start|Now Loading\n|Shape$|InitEnd|Exit \n|^GCTRL|^[0-9a-f]{16})')
SHORT = {'OK', 'ON', 'NO', 'No', 'DF', 'HP', 'LV'}
def records(d, align=16):
    """(오프셋, 바이트문자열, 슬롯크기) — 슬롯 = 정렬 끝까지 0 인 구간. align=4 면 4 정렬 레코드도(슬롯 4 단위)"""
    out = []
    for m in PAT.finditer(d):
        o = m.start()
        if o % align or (o and d[o - 1] != 0): continue
        s = m.group()[:-1]
        if not re.search(rb'[A-Za-z]{2}', s): continue
        end = o + len(s) + 1
        a = 16 if o % 16 == 0 else 4
        slot = (end + a - 1) & ~(a - 1)
        if any(d[end:slot]): continue
        out.append((o, s, slot - o))
    return out
def visible(s):
    t = s.decode('latin1')
    if t in SHORT: return True
    if SKIP.search(t) or len(t.strip()) <= 2: return False
    if not re.search(r'[a-z]{2}|[A-Z]{3}|\b(OK|Lv|HP|DF|ATK|SPD)\b', t): return False
    return True
