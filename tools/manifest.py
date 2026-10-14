"""Content manifest of a ROM: SHA-1 of the ARM9/ARM7 binaries, banner and every NitroFS file by path.
Two ROMs with the same manifest have identical content even if ndstool laid out the file table
differently (ndstool numbers folders in the order the OS lists them, which varies between machines).
Usage: manifest.py <rom.nds> <ndstool> [out.json]"""
import hashlib, json, os, subprocess, sys, tempfile

def manifest(rom, ndstool):
    with tempfile.TemporaryDirectory() as t:
        p = lambda n: os.path.join(t, n)
        subprocess.run([ndstool, "-x", rom, "-9", p("arm9"), "-7", p("arm7"), "-y9", p("y9"), "-y7", p("y7"),
                        "-t", p("banner"), "-d", p("fs")], check=True, stdout=subprocess.DEVNULL)
        h = lambda f: hashlib.sha1(open(f, "rb").read()).hexdigest()
        m = {k: h(p(k)) for k in ("arm9", "arm7", "y9", "y7", "banner")}
        for root, _, files in os.walk(p("fs")):
            for f in files:
                full = os.path.join(root, f)
                m["/" + os.path.relpath(full, p("fs")).replace(os.sep, "/")] = h(full)
    return dict(sorted(m.items()))

if __name__ == "__main__":
    m = manifest(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3:
        json.dump(m, open(sys.argv[3], "w"), indent=0)
    print(len(m), "entries")
