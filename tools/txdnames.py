import glob,re,collections,sys
c=collections.defaultdict(list)
for f in glob.glob('unp/**/*.txd',recursive=True):
    b=open(f,'rb').read()
    for m in re.finditer(rb'\x02\x00\x00\x00.\x00\x00\x00\x0a\x00\x02\x1c([ -~]{3,40}?)\x00',b,re.S):
        c[m.group(1).decode()].append(f)
for k,v in sorted(c.items()):
    if re.search(sys.argv[1],k): print(k,len(v),v[:2])
