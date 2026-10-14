#ifndef SGEN_H
#define SGEN_H

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

/* All generator state (the DS blob has no globals; this lives in a zero-filled area of the blob). */
typedef struct Work {
    u32 (*rng)(u32 range);          /* value in [0, range) — the game's rng_next on the DS */
    u8 row_of[81], col_of[81], box_of[81];
    u8 units[27][9];                /* 0-8 rows, 9-17 cols, 18-26 boxes */
    u8 sol[81], puz[81], tmp[81], order[81];
    u8 stk_idx[81];
    u16 stk_cand[81];
    u8 rb[81];                      /* rater board */
    u16 cand[81];                   /* rater candidates */
} Work;

int sgen_generate(Work *w, int difficulty, int max_attempts);
void sgen_write_record(Work *w, u8 *record);
int sgen_solve(Work *w, const u8 *puz);

#endif
