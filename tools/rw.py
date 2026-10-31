import struct
CONTAINERS={0x16,0x15,0x3,0x1}
def walk(b,p=0,end=None,depth=0,out=None):
    if out is None: out=[]
    end=len(b) if end is None else end
    while p+12<=end:
        t,l,v=struct.unpack_from('<III',b,p)
        out.append((depth,t,p,l))
        if t in (0x16,0x15,0x3) or (t==1 and depth>=1 and l>64):
            walk(b,p+12,min(p+12+l,end),depth+1,out)
        p+=12+l
    return out
