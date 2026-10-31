"""GS 로컬 메모리 배치(PSMCT32 <-> PSMT8) 변환. 버퍼 시작 0, BW 는 64픽셀 단위."""
import numpy as np
BLOCK32=[0,1,4,5,16,17,20,21,2,3,6,7,18,19,22,23,8,9,12,13,24,25,28,29,10,11,14,15,26,27,30,31]
COL32=[0,1,4,5,8,9,12,13,2,3,6,7,10,11,14,15]
BLOCK8=[0,1,4,5,16,17,20,21,2,3,6,7,18,19,22,23,8,9,12,13,24,25,28,29,10,11,14,15,26,27,30,31]
def addr32(x,y,bw):
    """바이트 주소"""
    page=(y//32)*bw+(x//64); px,py=x%64,y%32
    blk=BLOCK32[(py//8)*8+(px//8)]; bx,by=px%8,py%8
    col=by//2; cw=COL32[(by%2)*8+bx]
    return page*8192+blk*256+col*64+cw*4
# PSMT8 내부 배치(블록 16x16, 칼럼 16x4)
COL8=None
def _col8():
    t=np.zeros((4,16),int)
    # 표준 표 (GS 매뉴얼)
    tbl=[[0,4,16,20,32,36,48,52,2,6,18,22,34,38,50,54],
         [8,12,24,28,40,44,56,60,10,14,26,30,42,46,58,62],
         [33,37,49,53,1,5,17,21,35,39,51,55,3,7,19,23],
         [41,45,57,61,9,13,25,29,43,47,59,63,11,15,27,31]]
    return tbl
T8=_col8()
def addr8(x,y,bw):
    page=(y//64)*(bw//2)+(x//128); px,py=x%128,y%64
    blk=BLOCK8[(py//16)*8+(px//16)]; bx,by=px%16,py%16
    col=by//4; cy=by%4
    w=T8[cy][bx]
    if col%2: # 홀수 칼럼은 좌우 반전 패턴
        w=T8[(cy+2)%4][bx]
    return page*8192+blk*256+col*64+(w%16)*4+(w//16)
def unswizzle8(data,w,h):
    """CT32 (w/2 x h/2) 로 올린 데이터 -> 8bpp w x h"""
    mem=np.zeros(1<<22,np.uint8)
    cw,ch=w//2,h//2; bw=max(1,cw//64)
    src=np.frombuffer(data,np.uint8).reshape(ch,cw,4)
    for y in range(ch):
        for x in range(cw):
            a=addr32(x,y,bw); mem[a:a+4]=src[y,x]
    out=np.zeros((h,w),np.uint8); bw8=max(2,w//64)
    for y in range(h):
        for x in range(w):
            out[y,x]=mem[addr8(x,y,bw8)]
    return out
def swizzle8(img):
    h,w=img.shape;mem=np.zeros(1<<22,np.uint8);bw8=max(2,w//64)
    for y in range(h):
        for x in range(w): mem[addr8(x,y,bw8)]=img[y,x]
    cw,ch=w//2,h//2;bw=max(1,cw//64);out=np.zeros((ch,cw,4),np.uint8)
    for y in range(ch):
        for x in range(cw):
            a=addr32(x,y,bw);out[y,x]=mem[a:a+4]
    return out.tobytes()
def pal_unswizzle(p):
    p=np.frombuffer(p,np.uint8).reshape(256,4).copy();q=p.copy()
    for i in range(256):
        j=(i&0xe7)|((i&8)<<1)|((i&16)>>1); q[i]=p[j]
    return q
def _idx8(w,h):
    y,x=np.mgrid[0:h,0:w]
    block=(y&~0xf)*w+(x&~0xf)*2
    swap=(((y+2)>>2)&1)*4
    posY=(((y&~3)>>1)+(y&1))&7
    col=posY*w*2+((x+swap)&7)*4
    byte=((y>>1)&1)+((x>>2)&2)
    return block+col+byte
def unswizzle8(data,w,h):
    return np.frombuffer(data,np.uint8)[_idx8(w,h)]
def swizzle8(img):
    h,w=img.shape;out=np.zeros(w*h,np.uint8);out[_idx8(w,h)]=img;return out.tobytes()
