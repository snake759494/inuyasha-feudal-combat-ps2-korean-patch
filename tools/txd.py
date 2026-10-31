"""RenderWare PS2 TXD 텍스처 목록/정보"""
import struct
def textures(b):
    out=[];t,l,v=struct.unpack_from('<III',b,0);assert t==0x16,hex(t)
    p=12+12+4
    while p<12+l:
        t,cl,v=struct.unpack_from('<III',b,p)
        if t!=0x15: p+=12+cl;continue
        q=p+12
        q+=12+struct.unpack_from('<I',b,q+4)[0]
        nl=struct.unpack_from('<I',b,q+4)[0];name=b[q+12:q+12+nl].split(b'\0')[0].decode('latin1');q+=12+nl
        q+=12+struct.unpack_from('<I',b,q+4)[0]
        hq=q+12
        w,h,dep,fmt=struct.unpack_from('<4I',b,hq+12)
        dq=hq+12+struct.unpack_from('<I',b,hq+4)[0]
        dl=struct.unpack_from('<I',b,dq+4)[0]
        out.append(dict(name=name,off=p,size=12+cl,w=w,h=h,depth=dep,fmt=fmt,hdr=hq+12,dataoff=dq+12,datalen=dl))
        p+=12+cl
    return out
