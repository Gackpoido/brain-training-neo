/* DS blob (Fase 4 + 6). Loaded from /data/Sudoku/sgen.bin and run by the resident call_blob helper
 * (arm9 v21), OUTSIDE any file-loader callback, so the game's file functions may be used here.
 *
 * Entries (entry.s jump table, r2 = Work area):
 *   +0  blob_sel (bank, idx)       replaces difficulty_selector (same behaviour)
 *   +4  blob_cont(bank, number)    replaces FUN_020437cc (continue a saved game) + restores a
 *                                  saved random puzzle from the save's given-cell markers
 *   +8  blob_menu(menu_ctx, -)     after init_sudoku_puzzle_bank on the difficulty screen: in random
 *                                  mode generate a puzzle and skip the puzzle picker (0x81)
 *   +12 blob_save(cells, slots)    after pack_cells_into_save_buffer: store the givens of a random
 *                                  puzzle in the (otherwise unused) save slots of the given cells
 *   +16 blob_icon(tiles)          difficulty screen init: replace the "Leer" button tiles in OBJ VRAM
 *                                  with the dice graphic (only this screen; the Stay_s_ch file is untouched)
 *
 * Random puzzles are tagged in the 3 padding bytes of the 92-byte record (bank+0x249..0x24b, always
 * 0 in the game's .dat files). The resident stamp check reads bank+0x24b.
 */
#include "sgen.h"

#define RNG_NEXT          0x0204DFA0u   /* rng_next(range) */
#define DC_FLUSH_ALL      0x02006150u
#define LOAD_SUDOKUS      0x02067854u   /* (path, file_offset, dst, size) */
#define DAT_PATH_OTEGARU  0x020CDF78u   /* sudoku_problem_<d>.dat paths, 0x28 bytes apart */

#define BANK        (*(u8 **)0x020DD958u)    /* puzzle bank (difficulty_selector's ctx) */
#define SAVE_BUF    (**(u8 ***)0x020DA760u)  /* 0x1A4-byte Sudoku save of the current profile */
#define DLPLAY_BUF  (*(u8 **)0x020DA770u)    /* Download Play puzzle buffer */
#define RANDOM_FLAG (*(volatile u32 *)0x020D59BCu)   /* Leer toggle: 1 = random mode */
#define FADE_TARGET (*(volatile u32 *)0x020DD9CCu)   /* screen after the 0x43 fade (picker: 0x7e) */
#define DLG_TARGET  (*(volatile u32 *)0x020DDAACu)   /* 0x87 "no" / 0x88 "yes" target (picker: 0x84) */

#define B32(b, off) (*(int *)((b) + (off)))
#define B16(p, off) (*(u16 *)((p) + (off)))
#define ENTRY(b, i) ((b) + 0xC + (i) * 10)     /* number, src, file_idx, stamp_id (u16) + type (u8) */
#define RECORD(b)   ((b) + 0x1F0)

#define MARK0 'R'
#define MARK1 'N'
#define MARK2 0xA5

typedef void (*void_fn)(void);
typedef void (*load_fn)(const char *path, u32 offset, u8 *dst, u32 size);

static int is_marked(const u8 *bank)
{
    return bank[0x249] == MARK0 && bank[0x24A] == MARK1 && bank[0x24B] == MARK2;
}

static void mark(u8 *bank)
{
    bank[0x249] = MARK0;
    bank[0x24A] = MARK1;
    bank[0x24B] = MARK2;
}

/* Save slot of cell k = r*9+c is c*9+r (pack_cells_into_save_buffer walks the grid transposed). */
static int slot_of(int r, int c) { return (c * 9 + r) * 5; }

static int save_is_random(const u8 *save)
{
    int i;
    for (i = 0; i < 81 * 5; i += 5)
        if ((save[0xD + i] & 0xF) == 0xF)
            return 1;
    return 0;
}

/* Exact port of difficulty_selector (0x020438e8). */
int blob_sel(u8 *bank, int idx, Work *w)
{
    int i;
    (void)w;
    B32(bank, 8) = idx;
    if (idx >= 0 && idx < B32(bank, 0x1EC) && B16(ENTRY(bank, idx), 0) != 0xFFFF) {
        u8 *e = ENTRY(bank, idx);
        u8 *rec = RECORD(bank);
        for (i = 0; i < 0x5C; i++) rec[i] = 0;
        if (B16(e, 2) == 0) {
            ((void_fn)DC_FLUSH_ALL)();
            ((load_fn)LOAD_SUDOKUS)((const char *)(DAT_PATH_OTEGARU + 0x28 * B32(bank, 4)),
                                    B16(e, 4) * 0x5C, rec, 0x5C);
        } else if (B16(e, 2) == 1) {
            const u8 *src = DLPLAY_BUF + B16(e, 4) * 0x5C;
            for (i = 0; i < 0x5C; i++) rec[i] = src[i];
        }
        B32(bank, 0) = e[8];
    }
    bank[0x24C] = 0;
    bank[0x24D] = 0;
    return 0;
}

/* Rebuild a saved random puzzle: given cells carry (digit << 4) | 0xF in their save slot. */
static void restore_random(u8 *bank, Work *w)
{
    u8 *save = SAVE_BUF;
    int r, c, found = 0;
    for (r = 0; r < 9; r++)
        for (c = 0; c < 9; c++) {
            u8 v = save[0xD + slot_of(r, c)];
            u8 d = v >> 4;
            w->rb[r * 9 + c] = 0;
            if ((v & 0xF) == 0xF) {
                if (d < 1 || d > 9) return;
                w->rb[r * 9 + c] = d;
                found = 1;
            }
        }
    if (!found || save[5] != (u8)B32(bank, 4))
        return;
    if (!sgen_solve(w, w->rb))
        return;
    sgen_write_record(w, RECORD(bank));
    mark(bank);
}

/* Port of FUN_020437cc: select the bank entry with this puzzle number. */
int blob_cont(u8 *bank, u32 number, Work *w)
{
    int i, n = B32(bank, 0x1EC);
    for (i = 0; i < n; i++)
        if (number == B16(ENTRY(bank, i), 0)) {
            blob_sel(bank, i, w);
            restore_random(bank, w);
            return 1;
        }
    blob_sel(bank, -1, w);
    return 0;
}

int blob_menu(u8 *menu, u32 unused, Work *w)
{
    u8 *bank = BANK, *save;
    int i, n, d;
    (void)unused;
    if (!RANDOM_FLAG)
        return 0;
    d = B32(bank, 4);
    n = B32(bank, 0x1EC);
    for (i = 0; i < n; i++)              /* first normal (type 0) puzzle slot hosts the random one */
        if (B16(ENTRY(bank, i), 0) != 0xFFFF && ENTRY(bank, i)[8] == 0)
            break;
    if (i >= n)
        return 0;                        /* no usable slot: keep the normal picker */
    blob_sel(bank, i, w);
    w->rng = (u32 (*)(u32))RNG_NEXT;
    if (RECORD(bank)[4] == 0 && sgen_generate(w, d, 300)) {
        sgen_write_record(w, RECORD(bank));
        mark(bank);
    }
    save = SAVE_BUF;
    FADE_TARGET = 0x7E;
    if (B16(save, 6) == 0xFFFF) {
        B32(menu, 0x6C8) = 0x84;                         /* hints? -> new game */
    } else {
        DLG_TARGET = 0x84;
        if (save_is_random(save) && save[5] == (u8)d)
            B32(menu, 0x6C8) = 0x87;                     /* continue the saved random puzzle? */
        else
            B32(menu, 0x6C8) = 0x88;                     /* a new game erases the saved one */
    }
    return 1;
}

int blob_save(u8 *cells, u8 *slots, Work *w)
{
    int r, c;
    (void)w;
    if (!is_marked(BANK))
        return 0;
    for (r = 0; r < 9; r++)
        for (c = 0; c < 9; c++) {
            const u8 *cell = cells + (r * 9 + c) * 24;          /* SudokuCell, 24 bytes */
            if (*(const u32 *)cell == 0)                        /* state 0 = given */
                slots[slot_of(r, c)] = (u8)((cell[0xC] << 4) | 0xF);
        }
    return 1;
}

/* Stay tiles are loaded at engine-B OBJ VRAM 0x06607000 (tile 0x380, 2D mapping: 32 tiles per 1 KB row).
 * The Leer button (Stay.NCER cells 6/7/12) uses tiles 16-19 and 20-23 of rows 0-3 of that block.
 * VRAM only accepts 16/32-bit writes, so copy words. */
int blob_icon(const u32 *tiles, u32 unused, Work *w)
{
    int r, i;
    (void)unused; (void)w;
    for (r = 0; r < 4; r++) {
        volatile u32 *dst = (volatile u32 *)(0x06607000u + r * 0x400 + 16 * 32);
        for (i = 0; i < 64; i++)
            dst[i] = tiles[r * 64 + i];
    }
    return 1;
}
