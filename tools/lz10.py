"""LZ77 type 0x10 (GBA/NDS BIOS format) compressor + decompressor, used to pack sgen.bin into the
.cmp file the game's loader (FUN_02067760 -> FUN_02007d00) decompresses for us."""
import sys


def compress(data):
    out = bytearray([0x10, len(data) & 0xFF, (len(data) >> 8) & 0xFF, (len(data) >> 16) & 0xFF])
    i = 0
    while i < len(data):
        flag_pos = len(out); out.append(0); flags = 0
        for bit in range(8):
            if i >= len(data): break
            best_len, best_disp = 0, 0
            for disp in range(1, min(0x1000, i) + 1):
                n = 0
                while n < 18 and i + n < len(data) and data[i + n] == data[i - disp + n]:
                    n += 1
                if n > best_len:
                    best_len, best_disp = n, disp
                    if n == 18: break
            if best_len >= 3:
                flags |= 0x80 >> bit
                v = ((best_len - 3) << 12) | (best_disp - 1)
                out += bytes([v >> 8, v & 0xFF]); i += best_len
            else:
                out.append(data[i]); i += 1
        out[flag_pos] = flags
    while len(out) % 4: out.append(0)
    return bytes(out)


def decompress(d):
    assert d[0] == 0x10
    n = int.from_bytes(d[1:4], 'little'); o = bytearray(); i = 4
    while len(o) < n:
        f = d[i]; i += 1
        for b in range(8):
            if len(o) >= n: break
            if f & (0x80 >> b):
                x = d[i] << 8 | d[i + 1]; i += 2
                for _ in range((x >> 12) + 3): o.append(o[-((x & 0xFFF) + 1)])
            else:
                o.append(d[i]); i += 1
    return bytes(o)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    raw = open(src, 'rb').read()
    c = compress(raw)
    assert decompress(c) == raw, 'round-trip failed'
    open(dst, 'wb').write(c)
    print(f'{src}: {len(raw)} -> {dst}: {len(c)} bytes (round-trip OK)')
