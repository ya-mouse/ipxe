#!/usr/bin/python2.7
from struct import unpack, pack
import sys

types = {
    'H':  [ 0x2e, '<3H2IHI2H2IHIHIH' ],
    'L':  [ 0x28, '<3H2IHI2H2IHIH' ],
}

mips = {
'09':
  (
    ('com',  ( 0x00004520, 'H' )),
    ('rxp',  ( 0x000037f2, 'H' )),
    ('tpat', ( 0x000040d2, 'L' )),
    ('txp',  ( 0x00003b4e, 'L' )),
  ),
'06':
  (
    ('com',  ( 0x00003f3c, 'H' )),
    ('rxp',  ( 0x00003200, 'H' )),
    ('tpat', ( 0x00003b08, 'L' )),
    ('txp',  ( 0x00003508, 'L' )),
  ),
}

rv2p = {
'09':
  (
    ('rv2p_proc1', ( 0x0000498c, 0x248 )),
    ('rv2p_proc2', ( 0x00004bd4, 0x430 )),
  ),
'06':
  (
    ('rv2p_proc1', ( 0x000044c0, 0x248 )),
    ('rv2p_proc2', ( 0x00004708, 0x430 )),
  ),
}

def print_data(data):
    i=1
    for v in data:
         print('0x%08x,' % v),
         if i % 6 == 0:
             print('\n\t'),
         i += 1


rev=sys.argv[2]
with open(sys.argv[1]) as f:
    offset = 0xa0
    data = []
    hdrs = []
    print('/* %s */\nstatic const uint32_t bnx2_mips_%s_firmware[] = {\n\t' % (sys.argv[1], rev)),
    for name,p in mips[rev]:
        t=types[p[1]]
        f.seek(p[0]-t[0])
        hdr = unpack(t[1], f.read(t[0]))
        start = hdr[3]
        text_addr = hdr[4]
        text_len  = hdr[5]
        hdrs.extend(unpack('<4I', pack('>4I', hdr[3], hdr[4], hdr[5], offset)))
        hdrs.extend((0,)*6)
        data.extend(unpack('>%dI' % (text_len >> 2), f.read(text_len)))
        offset += text_len

    print_data(hdrs + data)

    print('\n};\n')

    data = []
    hdrs = []
    offset = 0x58
    print('/* %s */\nstatic const uint32_t bnx2_rv2p_%s_firmware[] = {\n\t' % (sys.argv[1], rev)),
    for name,p in rv2p[rev]:
        f.seek(p[0])
        hdrs.extend(unpack('<3I', pack('>3I', 0, p[1], offset)))
        hdrs.extend((0,)*8)
        data.extend(unpack('>%dI' % (p[1] >> 2), f.read(p[1])))
        offset += p[1]

    print_data(hdrs + data)

    print('\n};')
