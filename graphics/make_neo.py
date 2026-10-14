"""Adds a red "NEO" rubber stamp to the EU title screen (top screen, BG built from Title_bg_noe_ch at
tile 0, Title_bg_<lang>_ch at tile 64 and the shared map Title_bg_noe_sc.bin, palette Title_bg_pl).
- ink colour: palette 2 of Title_bg_pl (already a red->white ramp: idx 1 = red ... 15 = white), unused
  by the title maps;
- tiles: blank, map-unused tiles of the language sheets (same 56 indices in all 6 languages), written
  identically into every Title_bg_<lang>_ch, so the stamp shows in every language;
- map: the shared Title_bg_noe_sc.bin, only cells that were the white filler tile 63 are changed.
The screen is used rotated (book style): upright stamp coords (u right, v down) -> screen x = cx - v,
y = cy + u, like the logo text.
Usage: make_neo.py <extracted .../data/Title folder>   (files are modified in place)
"""
import math, struct, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import lz10
TITLE = sys.argv[1]
LANGS = "degfis"

def lz10_dec(d):
    n = d[1] | d[2] << 8 | d[3] << 16; o = bytearray(); i = 4
    while len(o) < n:
        f = d[i]; i += 1
        for b in range(8):
            if len(o) >= n: break
            if f & (0x80 >> b):
                x = d[i] << 8 | d[i + 1]; i += 2
                for _ in range((x >> 12) + 3): o.append(o[-((x & 0xFFF) + 1)])
            else:
                o.append(d[i]); i += 1
    return o

sc = bytearray(open(os.path.join(TITLE, "Title_bg_noe_sc.bin"), "rb").read())
sheets = {l: lz10_dec(open(os.path.join(TITLE, f"Title_bg_{l}_ch.cmp"), "rb").read()) for l in LANGS}
used = {struct.unpack_from("<H", sc, i * 2)[0] & 0x3FF for i in range(1024)}
free = [t for t in range(64, 576) if t not in used
        and all(not any(sheets[l][(t - 64) * 32:(t - 63) * 32]) for l in LANGS)]

# ---- stamp geometry (upright, pixels) ----
W, H = 62.0, 30.0
def seg(ax, ay, bx, by, w):
    def f(u, v):
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((u - ax) * dx + (v - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(u - ax - t * dx, v - ay - t * dy) <= w / 2
    return f
def rrect_ring(inset, rad, w):
    x0, y0, x1, y1 = inset, inset, W - inset, H - inset
    def f(u, v):
        du = max(x0 + rad - u, 0, u - (x1 - rad)); dv = max(y0 + rad - v, 0, v - (y1 - rad))
        if du > 0 and dv > 0: d = math.hypot(du, dv) - rad
        else: d = max(x0 - u, u - x1, y0 - v, v - y1) if not (x0 <= u <= x1 and y0 <= v <= y1) else -min(u - x0, x1 - u, v - y0, y1 - v)
        if du > 0 and dv > 0: return abs(d) <= w / 2
        return abs(d) <= w / 2
    return f
def ring(cx, cy, rx, ry, w):
    def f(u, v):
        a = math.atan2((v - cy) / ry, (u - cx) / rx)
        return min(math.hypot(u - cx - rx * math.cos(a + k * 0.04), v - cy - ry * math.sin(a + k * 0.04))
                   for k in range(-8, 9)) <= w / 2
    return f
SW = 3.4                      # letter stroke
top, bot = 7.2, 22.8          # cap top / baseline (stroke centres)
u0 = 8.0
shapes = [rrect_ring(1.6, 4.0, 2.6), rrect_ring(4.6, 2.2, 1.2)]
# N (width 13)
shapes += [seg(u0 + 1.7, top, u0 + 1.7, bot, SW), seg(u0 + 11.3, top, u0 + 11.3, bot, SW),
           seg(u0 + 1.7, top, u0 + 11.3, bot, SW)]
u1 = u0 + 13 + 4.5
# E (width 10.5)
shapes += [seg(u1 + 1.7, top, u1 + 1.7, bot, SW), seg(u1 + 1.7, top, u1 + 10.5, top, SW),
           seg(u1 + 1.7, 15.0, u1 + 9.0, 15.0, SW), seg(u1 + 1.7, bot, u1 + 10.5, bot, SW)]
u2 = u1 + 10.5 + 4.5
# O (width 14)
shapes += [ring(u2 + 7.0, 15.0, 5.3, 7.8, SW)]
ANGLE = math.radians(-8.0)
CX, CY = 68.0, 150.0          # screen position of the stamp centre (white area left of "TRAINING")

def ink(x, y):
    # screen -> upright (inverse of x = cx - v', y = cy + u', then un-rotate)
    up, vp = y - CY, CX - x
    c, s = math.cos(-ANGLE), math.sin(-ANGLE)
    u = up * c - vp * s + W / 2; v = up * s + vp * c + H / 2
    if not (-1 <= u <= W + 1 and -1 <= v <= H + 1): return False
    return any(f(u, v) for f in shapes)

R = 33
tiles = {}                    # (tx, ty) -> 64 pixel indices
for ty in range(int((CY - R) // 8), int((CY + R) // 8) + 1):
    for tx in range(int((CX - R) // 8), int((CX + R) // 8) + 1):
        pix = []
        for y in range(8):
            for x in range(8):
                n = sum(ink(tx * 8 + x + (i + .5) / 4, ty * 8 + y + (j + .5) / 4) for i in range(4) for j in range(4))
                c = n / 16
                pix.append(1 + round((1 - c) * 14))
        if any(p != 15 for p in pix):
            assert struct.unpack_from("<H", sc, (ty * 32 + tx) * 2)[0] & 0x3FF == 63, (tx, ty)
            tiles[(tx, ty)] = pix
assert len(tiles) <= len(free), (len(tiles), len(free))
print(f"stamp needs {len(tiles)} tiles, {len(free)} free")

for (tx, ty), pix in sorted(tiles.items()):
    t = free.pop(0)
    data = bytearray(32)
    for k, p in enumerate(pix):
        data[k // 2] |= p if k % 2 == 0 else p << 4
    for l in LANGS:
        sheets[l][(t - 64) * 32:(t - 63) * 32] = data
    struct.pack_into("<H", sc, (ty * 32 + tx) * 2, t | (2 << 12))

open(os.path.join(TITLE, "Title_bg_noe_sc.bin"), "wb").write(sc)
for l in LANGS:
    open(os.path.join(TITLE, f"Title_bg_{l}_ch.cmp"), "wb").write(lz10.compress(bytes(sheets[l])))
print("written to", os.path.normpath(TITLE))
