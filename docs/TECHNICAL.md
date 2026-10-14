# Brain Training NEO — technical notes

All addresses refer to the European release (`ANDP`, CRC32 `FE158662`). Its ARM9 is loaded at
`0x02000000` and has no overlays. Function names are the ones we gave them while reverse-engineering
in Ghidra.

## 1. The game's Sudoku data

### Puzzle files

`/data/Sudoku/sudoku_problem_{otegaru,easy,normal,hard}.dat` are arrays of 92-byte records:

| Offset | Size | Contents |
|---|---|---|
| 0 | 2 | puzzle number |
| 2 | 2 | stamp/record id |
| 4 | 1 | type (0 = normal, 2 = the first four "practice" puzzles of each bank) |
| 5 | 2 | difficulty, 1 |
| 7 | 41 | givens: 81 nibbles, cell `k = row*9+col`, even `k` in the high nibble, 0 = empty |
| 48 | 41 | solution, same packing |
| 89 | 3 | padding (always 0) |

The calibration (`prototype/calibrate.py`) shows that Easy and Medium are always solvable with naked
and hidden singles; their difficulty comes only from the clue count. About 58% of Hard puzzles need
pointing pairs or naked/hidden pairs.

### Puzzle bank (heap object, pointer at `0x020DD958`)

| Offset | Contents |
|---|---|
| +0x000 | mode (0 = no hints, 1 = hints, 2 = practice) |
| +0x004 | difficulty |
| +0x008 | selected index |
| +0x00C | 48 entries × 10 bytes: number, source (0 = .dat, 1 = Download Play), file index, stamp id, type |
| +0x1EC | entry count |
| +0x1F0 | the selected 92-byte record (+0x249..0x24B = its padding) |
| +0x24C | "continuing a saved game" flag |
| +0x24D | flag |

- `init_sudoku_puzzle_bank` (`0x02043A1C`) fills the table.
- `difficulty_selector` (`0x020438E8`) selects an entry and reads its record with
  `read_file_range(path, index*92, bank+0x1F0, 92)` (`0x02067854`).

### Save

The save is a single 0x1A4-byte block per profile. `save_sudoku_progress` (`0x020492F4`) writes it and
`write_sudoku_save` (`0x0202D2C0`) stores it, with 8 rotating copies.

| Offset | Contents |
|---|---|
| +0x00 | counter |
| +0x04 | mode |
| +0x05 | difficulty |
| +0x06 | puzzle number (0xFFFF = none) |
| +0x08 | timer |
| +0x0C | hints used |
| +0x0D | 81 × 5-byte cell slots |
| +0x1A2 | 16-bit checksum (`0xFFFF − byte sum`) |

- Slot of cell `(r,c)`: `(c*9+r)*5`. The game walks the grid transposed.
- Slot contents: user digits are stored as `digit<<4`; pencil marks as nine nibbles.
- **Given cells are never stored**: their slots stay 0, because on "continue" the givens are read
  again from the `.dat` by puzzle number (`select_puzzle_by_number`, `0x020437CC`).
- Starting a new game erases the save (`setup_puzzle_cells`, `0x02049394`). That is why the game warns
  with dialog 0x88.

### Screens

The screen request is the global `0x020DD9C8`; the current screen is `0x020DDA44`. `switch_screen`
(`0x0204E3B0`) destroys the current screen and initialises the new one. Sudoku screens:

| Code | Screen |
|---|---|
| 0x80 | Difficulty |
| 0x81 | Puzzle picker |
| 0x84 | "Hints?" |
| 0x87 | "Continue?" |
| 0x88 | "Erase saved game?" |
| 0x43 | Fade, then goes to the screen stored in `0x020DD9CC` |
| 0x7E/0x7F | Gameplay |

The dialog screens are handled by `message_dialog_state_machine` (`0x0205E340`).

## 2. Code injection

### Free space

The ARM9 binary has almost no free space. The loader only loads the original `arm9.bin` size, so
nothing can be appended. The few word-aligned zero gaps we use were checked for cross-references:
`0x020C93CC`, `0x020C941C`, `0x020C946C`, `0x020C955C` and `0x020D57FC`. `0x020D59BC` is the
random-mode flag (0 at boot).

The large space comes from **replacing `difficulty_selector`**: its logic was ported to C (`blob_sel`),
which frees its 308-byte body for the resident code (`src/arm9/resident.s`).

### `call_blob(a0, a1, entry)` (resident)

1. `get_file_size` + `allocate_memory` + `load_file_to_buffer("/data/Sudoku/sgen.bin")`.
2. `DC_FlushAll` + I-cache invalidate.
3. Call `blob + entry` (with `r2 =` blob base).
4. `free_memory`.

All file functions share one global file struct (`0x020E01D8`), so the blob must not run inside a
file-loader callback. That is why the blob is loaded this way instead of through
`load_file_with_callback`.

### The blob (`src/blob`)

The blob is position-independent C: no globals, all state in a 2 KB zero area at its end. The build
links it at two base addresses and compares the results to prove it is PIC. Data it needs, such as
the button graphic, is reached via `adr`. Its entry table:

| Offset | Function | Called from |
|---|---|---|
| +0 | `blob_sel(bank, idx)` | `difficulty_selector` (exact C port) |
| +4 | `blob_cont(bank, number)` | `select_puzzle_by_number`: port, plus restoring a random save |
| +8 | `blob_menu(menu_ctx)` | difficulty pressed |
| +12 | `blob_save(cells, slots)` | after `pack_cells_into_save_buffer` |
| +16 | `blob_icon(tiles)` | difficulty screen init: draws the dice button into OBJ VRAM |

### Hooks (`prebuilt/arm9_patches.json`)

| Address | Hook |
|---|---|
| `0x020437CC` | `select_puzzle_by_number` → `call_blob(+4)` |
| `0x02043744` | `get_current_stamp_id` → `h_stamp`: returns −1 for random puzzles, like Download Play puzzles, so no stamp/record is written |
| `0x0204ADA4/ADBC/ADD4` | difficulty buttons → `h_menu` (`init_sudoku_puzzle_bank` + `call_blob(+8)`) |
| `0x02049360` | save → `h_save` |
| `0x02050F84` | screen switch → `h_screen`: in random mode, a request for the picker (0x81) becomes the difficulty screen (0x80) |
| `0x0204B078` | difficulty screen init → `h_icon` |
| `0x0204B34C` | registers touch region id 8 (the button) |
| `0x0204ACF8` | toggle on touch: `flag ^= 1`, plays SFX 0x10 |
| `0x0204AED8` | draws the button every frame: Stay.NANR sequence 4/5 (pressed), palette 13 (green) or 9 (grey), plus a copy of the "Back" button's BG drop shadow |

### Random puzzles

- **Tag.** A generated record is tagged in its padding: `bank+0x249..0x24B = 'R','N',0xA5`. Every
  normal load clears the record first, so the tag can never be stale.
- **`blob_menu`.** If random mode is on, it loads the first type-0 slot, overwrites givens and solution
  with a generated puzzle and tags it. It then sets the next screen: 0x84 if there is no save, 0x87 if
  the save is a random puzzle of the same difficulty, otherwise 0x88.
- **Saving.** `blob_save` writes `(digit<<4) | 0xF` into the empty slots of the given cells. A low
  nibble of `0xF` cannot occur in a normal save, because pencil marks are 0–9.
- **Continuing.** `blob_cont` reads those markers back, solves the grid (it must have a unique
  solution) and rebuilds the record. A random save is therefore restored correctly even when continued
  from the picker in grey mode.

### Generator

The generator (`sgen.c`) is a port of the Python prototype:

1. A random full grid from an iterative bitmask backtracking solver (MRV).
2. Fisher–Yates digging with a uniqueness check, with clues removed in symmetric pairs. The symmetry
   is one of six modes, chosen per puzzle.
3. A human-technique rater: singles, pointing/box-line, naked/hidden pairs.

Targets per difficulty:

| Level | Clues | Allowed techniques |
|---|---|---|
| Otegaru | 38–40 | singles |
| Easy | 21–39 | singles |
| Medium | 20–29 | singles |
| Hard | 20–28 | up to pairs; 58% of the time it must need more than singles |

Randomness comes from the game's own RNG, `rng_next` (`0x0204DFA0`), which is seeded from the RTC.
Host validation: `src/blob/test_host.c` + `validate.py`.

## 3. Graphics

### Dice button

- The button is Stay.NCER cells 5/6/7/12: two 32×32 OBJs, tiles 16–23 of rows 0–3 of the Stay sheet.
  The sheet is loaded at engine-B OBJ VRAM `0x06607000`, with 2D mapping.
- `blob_icon` overwrites those 1 KB with the dice graphic after the Stay sheet has been loaded, so the
  "Read" button elsewhere in the game is unchanged. VRAM needs 16/32-bit writes.
- Palette 13 (Stay): 1 = green fill, F = white, 2..6 = anti-aliasing towards white, 7 = edge. The game
  replaces it with palette 9 (grey) when random mode is off.

### Title stamp

The EU title is the BG built from:
- `Title_bg_noe_ch` (tiles 0–63);
- `Title_bg_<lang>_ch` (from tile 64);
- the shared map `Title_bg_noe_sc.bin`;
- `Title_bg_pl.bin`.

Palette 2 is an unused red→white ramp. The stamp uses 41 of the 56 tiles that are blank and unused in
all six language sheets; only white filler cells (tile 63) of the map are changed.

### Banner and header

- **Banner:** "NEO" is added to line 1 of every title, and the CRC16 over `0x20..0x83F` is
  recalculated.
- **Header:** `ndstool -c` rewrites the card-bus settings (`0x60..0x67`) and recomputes the
  secure-area CRC (`0x6C`) over the *decrypted* area. `graphics/fix_header.py` restores both from the
  original, since the secure area itself is unchanged, and recomputes the header CRC.

### Language

The game stores its language in the save's system header, not in the firmware:

- 12 bytes, 8 copies at `.sav` offset `0x80 + k*0x8000`.
- Byte +6 is the language: 0/1 = en, 2 = fr, 3 = de, 4 = it, 5 = es, 6 = nl.
- Bytes +10..11 are a checksum: `0xFFFF − sum(bytes 0..9)`.

It is read from the firmware only when that byte is 0xFF, on the first boot.
