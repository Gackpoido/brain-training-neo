# Brain Training NEO

A ROM hack of the European release of **Dr Kawashima's Brain Training: How Old Is Your Brain?**
(Nintendo DS, game code `ANDP`) that adds **unlimited Sudoku puzzles generated on the console
itself**.

> This repository contains only original code and documentation. It does **not** contain the game,
> its code or its data. You need your own copy of the game.

## Features

- **Random Sudoku mode.** A new button with two dice on the Sudoku difficulty screen switches between
  the game's original puzzles (grey) and random mode (green). In random mode, tapping a difficulty
  generates a new puzzle and starts it straight away, without the puzzle selection screen.
- **Calibrated difficulty.** Every puzzle has a unique solution. Clue counts and the solving techniques
  required (singles, pointing pairs, naked/hidden pairs) match the game's own banks for each level.
- **Varied layouts.** Each puzzle uses a random clue symmetry: 180° rotation, horizontal or vertical
  mirror, either diagonal, or none.
- **Save and resume.** "Save and quit" works for random puzzles. The givens are stored in otherwise
  unused bytes of the normal save slot, so the save format is unchanged.
- **No stamps.** Random puzzles never award stamps or records, so they don't affect your progress on
  the original puzzles.
- **NEO branding.** A red "NEO" stamp on the title screen, and "NEO" in the DS menu title.
- **All six languages:** English, French, German, Spanish, Italian and Dutch.

## Installing (players)

Download `Brain Training NEO.bps` from the [Releases](../../releases) page and apply it to a clean dump
of the EU game, using [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) (in the browser) or
[Flips](https://github.com/Alcaro/Flips).

| | Size | CRC32 | SHA-1 |
|---|---|---|---|
| Required ROM | 16 MB | `FE158662` | `a4c8b20886cbfc44311658b97aeb23b407f7aba2` |
| Patched ROM (1.0) | 16 MB | `A110AEE2` | `d8cd186de0134ac21e5806c21851ddbb00a7ec24` |

Save files are compatible both ways with the original game. It has been tested in melonDS only.

## Building from source

Requirements: Python 3 and [ndstool](https://github.com/devkitPro/ndstool). For `--bps` you also
need [Flips](https://github.com/Alcaro/Flips).

```sh
python3 build.py "path/to/original.nds" --bps
# -> out/Brain Training NEO.nds, out/Brain Training NEO.bps
```

`build.py` checks the input ROM, extracts it, applies the ARM9 patches and adds the generator. It then
draws the dice button and the NEO stamp from your ROM's own graphics, rebuilds the ROM and verifies
its content against the official release. ndstool lays out the file table in the order the OS lists
folders, so on another machine the CRC may differ while the content (ARM9/ARM7, banner and every file)
is identical. `build.py` checks this.

Our ARM code ships pre-compiled in `prebuilt/`, so no ARM toolchain is needed. To rebuild it from
`src/` you need `arm-none-eabi-gcc`/`binutils`:

```sh
python3 build_code.py --rom "path/to/original.nds"
```

## Repository layout

| Path | Contents |
|---|---|
| `src/blob/` | The on-device generator, in C: solver, generator, difficulty rater and the hooks' logic. It is compiled as a position-independent blob (`/data/Sudoku/sgen.bin`). |
| `src/arm9/` | ARM assembly hooks patched into the game's ARM9 binary. |
| `prebuilt/` | Compiled blob template, the ARM9 patch list (addresses and new bytes, plus SHA-1 of the bytes they replace), and the content manifest of the release. |
| `graphics/` | Scripts that draw the dice button, the NEO stamp and the banner titles, and fix the ROM header. |
| `prototype/` | Python prototype of the generator and the calibration against the original puzzles. |
| `tools/` | LZ10 (de)compressor and the content manifest tool. |
| `docs/TECHNICAL.md` | How it works: reverse-engineered formats, hooks, memory map and design notes. |

## How it works (short version)

The generator is too large for the few free bytes in the game's ARM9 binary. It therefore lives in a
file on the cartridge's file system. A small resident hook loads that file into the heap, runs it and
frees it whenever it is needed: selecting a puzzle, continuing a save, saving, or entering the
difficulty screen. The game's original puzzle-selection function is reimplemented inside the blob,
which freed its 308 bytes in the ARM9 for all the resident hooks. See
[`docs/TECHNICAL.md`](docs/TECHNICAL.md) for the details.

## Credits and legal

Brain Training NEO was made with the help of Ghidra, melonDS, DeSmuME, ndstool and Flips.
"Brain Training", "Nintendo DS" and all game content are trademarks and property of Nintendo. This
project is not affiliated with or endorsed by Nintendo. The code in this repository is released
under the [MIT License](LICENSE).
