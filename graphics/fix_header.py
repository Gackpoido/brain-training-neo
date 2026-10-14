"""ndstool -c rewrites some header fields: the card-bus settings at 0x60-0x67 and the secure-area CRC at
0x6C (recomputed over the DECRYPTED secure area, so it no longer matches what a real card reports).
Our secure area is byte-identical to the original, so restore those fields from the original header
and recompute the header CRC16 (0x15E, over 0x000-0x15D). The used-ROM-size field (0x80) stays."""
import struct, sys
def crc16(d, c=0xFFFF):
    for x in d:
        c ^= x
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c
orig, rom = sys.argv[1], sys.argv[2]
o = open(orig, "rb").read(); r = bytearray(open(rom, "rb").read())
assert r[0x4000:0x8000] == o[0x4000:0x8000], "secure area differs from the original"
r[0x60:0x68] = o[0x60:0x68]
r[0x6C:0x6E] = o[0x6C:0x6E]
struct.pack_into("<H", r, 0x15E, crc16(r[:0x15E]))
open(rom, "wb").write(r)
print("header bytes still different from original:", [hex(i) for i in range(0x180) if o[i] != r[i]])
