"""Writes banner_neo.bin: the original banner with "NEO" added to the first title line of every language
(the title shown in the Nintendo DS menu). Banner v1: titles are UTF-16LE, 0x100 bytes each at 0x240
(JP, EN, FR, DE, IT, ES); CRC16 (poly 0xA001, init 0xFFFF) of 0x20..0x83F stored at 0x02.
Usage: make_banner.py <original banner.bin> <output banner.bin>"""
import os, struct, sys
SRC, DST = sys.argv[1], sys.argv[2]
TITLES = [
    "Brain Training NEO:\nHow Old Is Your Brain?\nNintendo",      # JP (EU banner uses English)
    "Brain Training NEO:\nHow Old Is Your Brain?\nNintendo",      # EN
    "Programme NEO\nd'entraînement cérébral\nNintendo",           # FR
    "Gehirn-Jogging NEO:\nWie fit ist Ihr Gehirn?\nNintendo",     # DE
    "Brain Training NEO\nNintendo",                               # IT
    "Brain Training NEO\nNintendo",                               # ES
]
def crc16(d):
    c = 0xFFFF
    for x in d:
        c ^= x
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c
b = bytearray(open(SRC, "rb").read())
assert struct.unpack_from("<H", b, 0)[0] == 1 and struct.unpack_from("<H", b, 2)[0] == crc16(b[0x20:0x840])
for i, t in enumerate(TITLES):
    enc = t.encode("utf-16le")
    assert len(enc) < 0x100
    b[0x240 + i * 0x100:0x340 + i * 0x100] = enc + bytes(0x100 - len(enc))
struct.pack_into("<H", b, 2, crc16(b[0x20:0x840]))
open(DST, "wb").write(b)
for i, l in enumerate(["JP", "EN", "FR", "DE", "IT", "ES"]):
    print(l, repr(b[0x240 + i * 0x100:0x340 + i * 0x100].decode("utf-16le").split("\0")[0]))
print("crc %04X" % struct.unpack_from("<H", b, 2)[0])
