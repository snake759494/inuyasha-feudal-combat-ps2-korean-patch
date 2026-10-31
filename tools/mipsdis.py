import sys
from capstone import *
d=open(sys.argv[1],'rb').read()
a=int(sys.argv[2],0);n=int(sys.argv[3],0)
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS64|CS_MODE_LITTLE_ENDIAN);md.skipdata=True
for i in md.disasm(d[a-0x100000+0x1000:a-0x100000+0x1000+n],a): print(f"{i.address:08x}: {i.mnemonic:8} {i.op_str}")
