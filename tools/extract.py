"""work/unp 의 모든 seq 에서 표시 문자열을 모아 translation/src.tsv 로 저장 (id, 출현수, 최소슬롯, 첫파일, 영문)"""
import sys, glob, os, collections
sys.path.insert(0, os.path.dirname(__file__))
import seqtext
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNP = os.path.join(R, 'work', 'unp')


def collect():
    u = collections.OrderedDict()
    for f in sorted(glob.glob(os.path.join(UNP, '**', '*.seq'), recursive=True)):
        d = open(f, 'rb').read()
        rel = os.path.relpath(f, UNP).replace(os.sep, '/')
        for o, s, sl in seqtext.records(d):
            if seqtext.visible(s):
                u.setdefault(s, []).append((rel, o, sl))
    return u


def esc(s):
    return s.decode('latin1').replace('\n', '\\n')


if __name__ == '__main__':
    u = collect()
    with open(os.path.join(R, 'translation', 'src.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        for i, (s, l) in enumerate(u.items()):
            w.write('%04d\t%d\t%d\t%s\t%s\n' % (i, len(l), min(x[2] for x in l), l[0][0], esc(s)))
    print(len(u), sum(len(k) for k in u))
