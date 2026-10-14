#!/usr/bin/env python3
"""Developer tool: rebuilds prebuilt/ from the sources in src/ with the arm-none-eabi toolchain.

    python3 build_code.py --rom "original.nds" [--ndstool ndstool]

Outputs
  prebuilt/sgen_template.bin  the on-device blob (src/blob), with a zero-filled placeholder where
                              build.py later puts the dice button graphic (taken from the user's ROM)
  prebuilt/arm9_patches.json  every ARM9 change: address, new bytes (our code only) and the SHA-1 of
                              the original bytes it replaces (so no game code is stored here)

The original ROM is only needed to compute those SHA-1s. Toolchain: arm-none-eabi-gcc/as/ld/objcopy
(the blob is linked at two base addresses and compared, to prove it is position independent).
"""
import argparse, hashlib, json, os, shutil, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
PREBUILT = os.path.join(HERE, "prebuilt")
BASE = 0x02000000

# Game addresses (EU "Brain Training", ANDP). See docs/TECHNICAL.md for what they are.
SYMS = {
    "GET_FILE_SIZE": 0x02067B04, "ALLOCATE_MEMORY": 0x020516A0, "LOAD_FILE_TO_BUFFER": 0x02067988,
    "DC_FLUSH_ALL": 0x02006150, "FREE_MEMORY": 0x02051644, "INIT_PUZZLE_BANK": 0x02043A1C,
    "PACK_CELLS": 0x020482A8, "SCREEN_SWITCH": 0x0204E3B0, "STAMP_ORIG_NEXT": 0x02043748,
    "BLOB_PATH": 0x020C955C, "RANDOM_FLAG": 0x020D59BC, "SCREEN_REQUEST": 0x020DD9C8,
    "SET_SUBSLOT_STATE": 0x0206930C,
    "FUN_02055bac": 0x02055BAC,                      # play_ui_sfx
    "DEFAULT_LABEL": 0x0204AE28, "ORIGINAL_ADDLS": 0x0204ACFC,
    "get_touched_region_id": 0x0206AC3C, "FUN_02069178": 0x02069178, "FUN_02068ae4": 0x02068AE4,
    "PART_B": 0x020C946C, "LEER_SHADOW": 0x020D57FC, "RETURN_POINT": 0x0204AEDC,
    "REGISTER_TOUCH_REGION": 0x0206A7BC, "FUN_0208F510": 0x0208F510,
}
# (source file, link address, size of the original region it occupies, extra symbol overrides)
PIECES = [
    ("resident.s",       0x020438E8, 308, {}),   # difficulty_selector body + literal pool
    ("toggle_button.s",  0x020C93CC, 48,  {}),
    ("draw_button_a.s",  0x020C941C, 56,  {}),
    ("draw_button_b.s",  0x020C946C, 36,  {}),
    ("button_shadow.s",  0x020D57FC, 40,  {}),
    ("register_button.s", 0x020D5984, 56, {"RETURN_POINT": 0x0204B354}),
]

def run(*cmd, **kw):
    subprocess.run(cmd, check=True, **kw)

def branch(src, dst, link=False):
    return struct.pack("<I", (0xEB000000 if link else 0xEA000000) | (((dst - src - 8) >> 2) & 0xFFFFFF))

def assemble(tmp, name, addr, overrides):
    syms = dict(SYMS, **overrides)
    obj, elf, out = (os.path.join(tmp, name + e) for e in (".o", ".elf", ".bin"))
    run("arm-none-eabi-as", "-march=armv5te", os.path.join(SRC, "arm9", name), "-o", obj)
    run("arm-none-eabi-ld", obj, "-o", elf, f"-Ttext=0x{addr:08x}", "-e", "_start",
        *[f"--defsym={k}=0x{v:08x}" for k, v in syms.items()])
    run("arm-none-eabi-objcopy", "-O", "binary", "--only-section=.text", elf, out)
    nm = subprocess.run(["arm-none-eabi-nm", elf], capture_output=True, text=True, check=True).stdout
    labels = {f[2]: int(f[0], 16) for f in (l.split() for l in nm.splitlines()) if len(f) == 3 and f[1] in "Tt"}
    return open(out, "rb").read(), labels

def build_blob(tmp):
    cflags = ["-march=armv5te", "-mtune=arm946e-s", "-marm", "-mfloat-abi=soft", "-O2", "-ffreestanding",
              "-fno-builtin", "-fno-tree-loop-distribute-patterns", "-fno-jump-tables",
              "-fno-tree-switch-conversion", "-fno-pic", "-fno-stack-protector", "-nostdlib", "-Wall"]
    b = os.path.join(SRC, "blob")
    open(os.path.join(tmp, "button_tiles.bin"), "wb").write(bytes(1024))
    run("arm-none-eabi-gcc", *cflags, "-c", os.path.join(b, "sgen.c"), "-o", os.path.join(tmp, "sgen.o"))
    run("arm-none-eabi-gcc", *cflags, "-c", os.path.join(b, "blob_main.c"), "-o", os.path.join(tmp, "blob_main.o"))
    run("arm-none-eabi-as", "-march=armv5te", "-I", tmp, os.path.join(b, "entry.s"), "-o", os.path.join(tmp, "entry.o"))
    bins = []
    for base in (0, 0x2340000):
        elf = os.path.join(tmp, f"sgen_{base:x}.elf")
        run("arm-none-eabi-ld", "-T", os.path.join(b, "blob.ld"), f"--defsym=BASE=0x{base:x}",
            *(os.path.join(tmp, f) for f in ("entry.o", "blob_main.o", "sgen.o")), "-o", elf)
        run("arm-none-eabi-objcopy", "-O", "binary", elf, elf + ".bin")
        bins.append(open(elf + ".bin", "rb").read())
    assert bins[0] == bins[1], "blob is not position independent"
    nm = subprocess.run(["arm-none-eabi-nm", os.path.join(tmp, "sgen_0.elf")], capture_output=True,
                        text=True, check=True).stdout
    tiles = next(int(f[0], 16) for f in (l.split() for l in nm.splitlines()) if len(f) == 3 and f[2] == "button_tiles")
    return bins[0], tiles

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rom", required=True, help="clean EU ROM (only used to hash the replaced bytes)")
    ap.add_argument("--ndstool", default="ndstool")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        run(a.ndstool, "-x", a.rom, "-9", os.path.join(tmp, "arm9.bin"), stdout=subprocess.DEVNULL)
        arm9 = open(os.path.join(tmp, "arm9.bin"), "rb").read()
        patches, labels = [], {}

        def add(addr, new, what):
            old = arm9[addr - BASE:addr - BASE + len(new)]
            patches.append({"addr": f"0x{addr:08X}", "new": new.hex(), "what": what,
                            "orig_sha1": hashlib.sha1(old).hexdigest()})

        for name, addr, size, ov in PIECES:
            code, lab = assemble(tmp, name, addr, ov)
            assert len(code) <= size, (name, len(code), size)
            labels.update(lab)
            add(addr, code + bytes(size - len(code)), f"{name} (region of {size} bytes)")
        add(0x020C955C, b"/data/Sudoku/sgen.bin\0", "blob path string (unused zero gap)")
        call_blob = labels["call_blob"]
        add(0x020437CC, bytes.fromhex("0420a0e3") + branch(0x020437D0, call_blob),
            "select_puzzle_by_number -> blob_cont (mov r2,#4; b call_blob)")
        add(0x02043744, branch(0x02043744, labels["h_stamp"]), "get_current_stamp_id -> h_stamp")
        for at in (0x0204ADA4, 0x0204ADBC, 0x0204ADD4):
            add(at, branch(at, labels["h_menu"], True), "difficulty pressed: bl init_sudoku_puzzle_bank -> h_menu")
        add(0x02049360, branch(0x02049360, labels["h_save"], True), "save & exit: bl pack_cells -> h_save")
        add(0x02050F84, branch(0x02050F84, labels["h_screen"], True), "screen switch -> h_screen")
        add(0x0204B078, branch(0x0204B078, labels["h_icon"], True), "difficulty screen init -> h_icon")
        add(0x0204ACF8, branch(0x0204ACF8, 0x020C93CC, True), "menu touch dispatch -> toggle_button")
        add(0x0204AED8, branch(0x0204AED8, 0x020C941C, True), "menu per-frame draw -> draw_button_a")
        add(0x0204B34C, branch(0x0204B34C, 0x020D5984, True), "difficulty screen init -> register_button")

        blob, tiles = build_blob(tmp)
    os.makedirs(PREBUILT, exist_ok=True)
    open(os.path.join(PREBUILT, "sgen_template.bin"), "wb").write(blob)
    json.dump({"arm9_size": len(arm9), "arm9_sha1": hashlib.sha1(arm9).hexdigest(),
               "blob_tiles_offset": tiles, "blob_tiles_size": 1024, "patches": patches},
              open(os.path.join(PREBUILT, "arm9_patches.json"), "w"), indent=1)
    print(f"prebuilt/: {len(patches)} ARM9 patches, blob {len(blob)} bytes (tiles at 0x{tiles:x})")

if __name__ == "__main__":
    main()
