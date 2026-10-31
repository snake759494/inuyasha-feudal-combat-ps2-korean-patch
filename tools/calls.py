import struct,sys
d=open(sys.argv[1],'rb').read()
N=0x32f15c//4;W=struct.unpack_from('<%dI'%N,d,0x1000)
for t in sys.argv[2:]:
    t=int(t,0);enc=0x0c000000|((t>>2)&0x3ffffff)
    print(hex(t),[hex(0x100000+i*4) for i,w in enumerate(W) if w==enc])
