import struct,sys
d=open(sys.argv[1],'rb').read()
W=struct.unpack_from('<%dI'%((0x32f15c)//4),d,0x1000)
def va(i): return 0x100000+i*4
targets=[int(x,0) for x in sys.argv[2:]]
for t in targets:
    hi=(t+0x8000)>>16; lo=t&0xffff
    for i,w in enumerate(W):
        if (w>>26)==0x0f and (w&0xffff)==hi:
            r=(w>>16)&31
            for j in range(i+1,min(i+40,len(W))):
                x=W[j]
                if (x>>21)&31==r and (x&0xffff)==lo and (x>>26) in (0x09,0x23,0x2b,0x24,0x25,0x20,0x21,0x0d):
                    print(hex(t),hex(va(i)),hex(va(j)));break
