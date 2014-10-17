#!/usr/bin/python3
from struct import unpack, pack
import sys

# Exit codes:
#   1 - wrong program arguments
# 254 - unknown RV2P firmware sizes
# 255 - unable to find firmware in the Option ROM

# Define MIPS FW header types.
#  - 0x2e met in BCM5709 for COM and RXP
#  - 0x28 met in all procs in BCM5706 and BCM5709 for the rest
types = (
    # size, unpack format
    ( 0x2e, '<3H2IHI2H2IHIHIH' ),
    ( 0x28, '<3H2IHI2H2IHIH' ),
)

# Search for proper FW header location
def get_header(content, offset):
    for t in types:
        hdr = unpack(t[1], content[offset-t[0]:offset])
        # hdr[3] -- entry point address
        # hdr[4] -- .text.addr field
        # hdr[5] -- .text.len field
        # Checking for address values. Address should start from 0x08000000
        if not (hdr[3] & 0x08000000) or not (hdr[4] & 0x08000000):
            continue
        if verbose:
            sys.stderr.write('--> FW %s: (%08x,%08x,%x)\n\t' % (item, hdr[3], hdr[4], hdr[5]))
            i = 1
            for b in hdr:
                sys.stderr.write('%x ' % b)
                # Format output by six numbers
                if i % 6 == 0:
                    sys.stderr.write('\n\t')
                i += 1
            sys.stderr.write('\n')
        return hdr
    return None

def print_data(data):
    i = 1
    for v in data:
        sys.stdout.write('0x%08x, ' % v)
        # Format output by six numbers
        if i % 6 == 0:
            sys.stdout.write('\n\t')
        i += 1

def print_struct(name, rev, data):
    sys.stdout.write('/* %s */\nstatic const uint32_t bnx2_%s_%s_firmware[] = {\n\t' % (sys.argv[1], name, rev))
    print_data(data)
    sys.stdout.write('\n};\n')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: genbnx2 option.rom REV-NUMBER [-v]')
        sys.exit(1)

    f = open(sys.argv[1], 'rb')
    content = f.read()
    rev = sys.argv[2]
    verbose = len(sys.argv) == 4 and sys.argv[3] == '-v'

    data = []
    hdrs = []
    max_offset = 0
    has_error = False
    # Size of the MIPS FW header in resulted structure is 0xa0 bytes:
    # 4 * sizeof(bnx2_mips_fw_file_entry)
    offset = 0xa0
    for item in ('com','rxp','tpat','txp'):
        # Reverse FW name (BE order) and pad to 4 chars with space
        key = bytes(('%-4s' % item)[::-1], 'ascii')

        # Matched FW name is at `-0x10' offset from the beginning
        start_off = content.find(key) - 0x10
        if start_off < 0:
            sys.stderr.write('Unable to find MIPS firmware for: %s\n' % item)
            has_error = True
            continue
        if has_error:
            continue

        max_offset = max(max_offset, start_off)

        # Parse FW header
        hdr = get_header(content, start_off)
        if hdr is None:
            sys.stderr.write('Unable to find header for MIPS firmware: %s\n' % item)
            has_error = True
            continue
        # Push header data in BE order
        hdrs.extend(unpack('<4I', pack('>4I', hdr[3], hdr[4], hdr[5], offset)))
        hdrs.extend((0,)*6)
        # Push firmware data in BE order
        data.extend(unpack('>%dI' % (hdr[5] >> 2), content[start_off:start_off+hdr[5]]))
        offset += hdr[5]

    if has_error:
        sys.exit(255)

    # Search for RV2P file offset (at least 0x50 zeroes and 0x0800000,0x010000ac dword)
    file_offset = content[max_offset:].find(bytes((0x00,)*0x50 + (8,0,0,0) + (1,0,0,0xac)))
    if file_offset < 0:
        sys.stderr.write('Unable to find RV2P firmware beggining sequence\n')
        sys.exit(255)
    # Make file offset to RV2P FW from the content's beggining
    file_offset += max_offset + 0x50

    # Check for RV2P size by asm opcodes
    #   push large 0x248
    push_size1 = content.find(bytes((0x66,0x68,0x48,0x02,0x00,0x00)))
    #   push large 0x430
    push_size2 = content.find(bytes((0x66,0x68,0x30,0x04,0x00,0x00)))
    if push_size1 < 0 or push_size2 < 0 or push_size1 > push_size2:
        sys.stderr.write('RV2P size mismatch\n')
        sys.exit(254)

    # Print MIPS firmware structure
    print_struct('mips', rev, hdrs + data)

    data = []
    hdrs = []
    # Size of the RV2P FW header in resulted structure is 0x58 bytes:
    # 2 * sizeof(bnx2_rv2p_fw_file_entry)
    offset = 0x58
    # RV2P_PROC1 has length 0x248, PROC2 has 0x430
    for text_len in 0x248, 0x430:
        hdrs.extend(unpack('<3I', pack('>3I', 0, text_len, offset)))
        hdrs.extend((0,)*8)
        data.extend(unpack('>%dI' % (text_len >> 2), content[file_offset:file_offset+text_len]))
        offset += text_len
        file_offset += text_len

    # Print RV2P firmware structure
    print_struct('rv2p', rev, hdrs + data)
