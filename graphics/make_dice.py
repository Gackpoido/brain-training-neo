"""Language-independent alternative for the random-mode button: two dice (faces 5 and 3) drawn in
the button style of Stay palette 13 (white F bodies, anti-aliasing 2..6 towards the green fill,
pips cut out in the fill colour). 8x8 supersampled.
Upright coordinates: column = raw sprite Y, row = raw sprite x (inner fill: x 7..26, Y 9..58).
Usage: make_dice.py <Stay_s_ch decompressed> <out tiles.bin>
"""
import math, sys

sheet = open(sys.argv[1], "rb").read()
def px(x, y):
    t = (y // 8) * 32 + (x // 8); o = t * 32 + (y % 8) * 4 + (x % 8) // 2
    return sheet[o] & 15 if x % 2 == 0 else sheet[o] >> 4
out = [[px(128 + x, Y) if Y < 32 else px(160 + x, Y - 32) for Y in range(64)] for x in range(32)]
for x in range(8, 26):
    for Y in range(9, 59):
        out[x][Y] = 1                                    # wipe "Leer"

SIZE, RADIUS, PIP = 16.0, 3.2, 1.75                     # die edge, corner radius, pip radius
def rounded_rect(u, v, u0, v0):
    du = max(u0 + RADIUS - u, 0, u - (u0 + SIZE - RADIUS))
    dv = max(v0 + RADIUS - v, 0, v - (v0 + SIZE - RADIUS))
    return math.hypot(du, dv) <= RADIUS
FACES = {5: [(0.27, 0.27), (0.73, 0.27), (0.5, 0.5), (0.27, 0.73), (0.73, 0.73)],
         3: [(0.27, 0.73), (0.5, 0.5), (0.73, 0.27)]}
dice = []                                                # (u0 = Y, v0 = row offset from x=24, face)
GAP = 4.0
total = 2 * SIZE + GAP
u_start = 9 + (50 - total) / 2
v_start = 1.0                                            # rows x 24..9 (inner fill is x 7..26)
for k, face in enumerate((5, 3)):
    dice.append((u_start + k * (SIZE + GAP), v_start, face))

def whiteness(u, v):
    for u0, v0, face in dice:
        if rounded_rect(u, v, u0, v0):
            for fu, fv in FACES[face]:
                if math.hypot(u - (u0 + fu * SIZE), v - (v0 + fv * SIZE)) <= PIP:
                    return 0
            return 1
    return 0

def level(w):
    if w < 0.12: return 1
    if w > 0.85: return 0xF
    return 2 + min(4, int((w - 0.12) / 0.73 * 5))

for row in range(0, 19):                                 # v = row -> raw x = 25 - row
    x = 25 - row
    for Y in range(9, 59):
        w = sum(whiteness(Y + (i + .5) / 8, row + (j + .5) / 8) for i in range(8) for j in range(8)) / 64
        if w >= 0.12:
            out[x][Y] = level(w)

for x in range(30, 3, -1):
    print(f"{x:3d} " + "".join(" " if out[x][Y] == 0 else ("." if out[x][Y] == 1 else "0123456789ABCDEF"[out[x][Y]]) for Y in range(4, 64)))

res = bytearray(1024)
for Y in range(64):
    for x in range(32):
        sx = (0 if Y < 32 else 32) + x; sy = Y % 32
        o = ((sy // 8) * 8 + sx // 8) * 32 + (sy % 8) * 4 + (sx % 8) // 2
        res[o] |= out[x][Y] if sx % 2 == 0 else out[x][Y] << 4
open(sys.argv[2], "wb").write(res)
