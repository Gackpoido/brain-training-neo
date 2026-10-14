#!/usr/bin/env python3
"""Builds "Brain Training NEO" from your own clean EU ROM, and optionally the BPS patch.

    python3 build.py "Dr Kawashima's Brain Training - How Old Is Your Brain (Europe) (En,Fr,De,Es,It,Nl).nds"
    python3 build.py original.nds --bps            # also writes out/Brain Training NEO.bps (needs flips)

Requirements: Python 3, ndstool (devkitPro), and Flips for --bps. No ARM toolchain is needed: our code
is shipped pre-compiled in prebuilt/ (rebuild it from src/ with build_code.py).

Steps: check the ROM -> extract it -> apply the ARM9 patches -> put the on-device generator
(/data/Sudoku/sgen.bin) with the dice button drawn from your ROM's own button frame -> add the "NEO"
stamp to the title screen and to the DS-menu title -> rebuild -> restore the original card settings in
the header -> pad to 16 MB -> compare the content with the official release -> optional BPS.

About reproducibility: ndstool numbers the NitroFS folders in the order the operating system lists
them, so the file-table layout (and therefore the ROM's CRC) can differ from machine to machine. The
content (ARM9/ARM7, banner and every file) is checked against prebuilt/release_manifest.json, which
holds the SHA-1s of the official 1.0 release (CRC32 A110AEE2).
"""
import argparse, hashlib, json, os, shutil, struct, subprocess, sys, tempfile, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import lz10, manifest

SOURCE_SHA1 = "a4c8b20886cbfc44311658b97aeb23b407f7aba2"   # clean EU dump, CRC32 FE158662
RESULT_CRC32 = 0xA110AEE2                                    # Brain Training NEO 1.0
BASE = 0x02000000

def run(*cmd, quiet=True):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL if quiet else None)

def find_tool(name, given):
    path = given or shutil.which(name)
    if not path:
        sys.exit(f"error: '{name}' not found (install it or pass --{name} PATH)")
    return path

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom", help="clean EU ROM (ANDP), SHA-1 " + SOURCE_SHA1)
    ap.add_argument("--out", default=os.path.join(HERE, "out"), help="output folder (default: out/)")
    ap.add_argument("--bps", action="store_true", help="also create the BPS patch (needs flips)")
    ap.add_argument("--ndstool"); ap.add_argument("--flips")
    a = ap.parse_args()
    ndstool = find_tool("ndstool", a.ndstool)

    src = open(a.rom, "rb").read()
    if hashlib.sha1(src).hexdigest() != SOURCE_SHA1:
        sys.exit("error: this is not the clean EU ROM (SHA-1 " + SOURCE_SHA1 + ")")
    info = json.load(open(os.path.join(HERE, "prebuilt", "arm9_patches.json")))
    os.makedirs(a.out, exist_ok=True)
    out_rom = os.path.join(a.out, "Brain Training NEO.nds")

    with tempfile.TemporaryDirectory() as w:
        j = lambda *p: os.path.join(w, *p)
        os.makedirs(j("fs"))
        run(ndstool, "-x", a.rom, "-9", j("arm9.bin"), "-7", j("arm7.bin"), "-y9", j("y9.bin"),
            "-y7", j("y7.bin"), "-t", j("banner.bin"), "-h", j("header.bin"), "-d", j("fs"))
        # The original NitroFS root also holds an empty file "%SDK_ASR" (file id 0); NEO is built (and was
        # tested) with the "data" folder only. The game opens files by path, so ids shifting is harmless.
        os.remove(j("fs", "%SDK_ASR"))
        data = j("fs", "data")

        # 1. ARM9 patches
        arm9 = bytearray(open(j("arm9.bin"), "rb").read())
        assert hashlib.sha1(arm9).hexdigest() == info["arm9_sha1"]
        for p in info["patches"]:
            at, new = int(p["addr"], 16) - BASE, bytes.fromhex(p["new"])
            assert hashlib.sha1(arm9[at:at + len(new)]).hexdigest() == p["orig_sha1"], p["addr"]
            arm9[at:at + len(new)] = new
        open(j("arm9.bin"), "wb").write(arm9)

        # 2. generator blob + dice button (drawn over the button frame of the game's Stay_s_ch sheet)
        open(j("stay_s_ch.bin"), "wb").write(lz10.decompress(open(os.path.join(data, "Menu", "Stay", "Stay_s_ch.cmp"), "rb").read()))
        run(sys.executable, os.path.join(HERE, "graphics", "make_dice.py"), j("stay_s_ch.bin"), j("dice.bin"))
        blob = bytearray(open(os.path.join(HERE, "prebuilt", "sgen_template.bin"), "rb").read())
        o = info["blob_tiles_offset"]
        blob[o:o + info["blob_tiles_size"]] = open(j("dice.bin"), "rb").read()
        open(os.path.join(data, "Sudoku", "sgen.bin"), "wb").write(blob)

        # 3. "NEO" title stamp (in place) and DS-menu title
        print("drawing the NEO title stamp...")
        run(sys.executable, os.path.join(HERE, "graphics", "make_neo.py"), os.path.join(data, "Title"))
        run(sys.executable, os.path.join(HERE, "graphics", "make_banner.py"), j("banner.bin"), j("banner_neo.bin"))

        # 4. rebuild, fix the header, pad like the original dump
        run(ndstool, "-c", out_rom, "-9", j("arm9.bin"), "-7", j("arm7.bin"), "-y9", j("y9.bin"),
            "-y7", j("y7.bin"), "-d", j("fs"), "-t", j("banner_neo.bin"), "-h", j("header.bin"))
        run(sys.executable, os.path.join(HERE, "graphics", "fix_header.py"), a.rom, out_rom)
    rom = open(out_rom, "rb").read()
    assert len(rom) == struct.unpack_from("<I", rom, 0x80)[0] <= len(src)
    rom += b"\xff" * (len(src) - len(rom))
    open(out_rom, "wb").write(rom)
    crc = zlib.crc32(rom)
    same = manifest.manifest(out_rom, ndstool) == json.load(open(os.path.join(HERE, "prebuilt", "release_manifest.json")))
    print(f"{out_rom}\n  CRC32 {crc:08X}  SHA-1 {hashlib.sha1(rom).hexdigest()}")
    if crc == RESULT_CRC32:
        print("  byte-identical to the official release")
    elif same:
        print("  content identical to the official release (only the file-table layout differs, see above)")
    else:
        sys.exit("  error: content DIFFERS from the official release")

    if a.bps:
        flips = find_tool("flips", a.flips)
        bps = os.path.join(a.out, "Brain Training NEO.bps")
        if os.path.exists(bps): os.remove(bps)
        run(flips, "--create", "--bps-delta", a.rom, out_rom, bps)
        check = os.path.join(a.out, ".check.nds")
        run(flips, "--apply", bps, a.rom, check)
        ok = open(check, "rb").read() == rom; os.remove(check)
        print(f"{bps}  ({os.path.getsize(bps)} bytes, round trip {'OK' if ok else 'FAILED'})")

if __name__ == "__main__":
    main()
