/* On-device Sudoku generator for Brain Training (ANDP), Fase 4.
 *
 * Port of sudoku_generator/{core,techniques,generate}.py. Built twice:
 *  - for the DS as a position-independent blob (entry.s calls blob_main), loaded and run by the
 *    difficulty_selector hook, overwriting the 92-byte puzzle record at ctx+0x1F0;
 *  - for the host (test_host.c) to validate it against the Python generator.
 *
 * Constraints for the DS build: no globals/statics (PIC blob, all state lives in struct Work),
 * no libc, no division by variables, bounded stack (the solver is iterative).
 */
#include "sgen.h"

#define ALL 0x1FF

#define TIER_SINGLE   1
#define TIER_POINTING 2
#define TIER_PAIR     3

static int popcount9(unsigned m)
{
    int n = 0;
    while (m) { m &= m - 1; n++; }
    return n;
}

static int lowest_digit(unsigned m)   /* bit d-1 set -> d */
{
    int d = 1;
    while (!(m & 1)) { m >>= 1; d++; }
    return d;
}

static void build_tables(Work *w)
{
    int i, u, k;
    for (i = 0; i < 81; i++) {
        int r = i / 9, c = i % 9;
        w->row_of[i] = r;
        w->col_of[i] = c;
        w->box_of[i] = (r / 3) * 3 + c / 3;
    }
    /* units 0-8 rows, 9-17 cols, 18-26 boxes */
    for (u = 0; u < 9; u++)
        for (k = 0; k < 9; k++) {
            w->units[u][k] = u * 9 + k;
            w->units[9 + u][k] = k * 9 + u;
            w->units[18 + u][k] = ((u / 3) * 3 + k / 3) * 9 + (u % 3) * 3 + k % 3;
        }
}

/* ---- backtracking solver (core.py count_solutions / generate_full_solution) ---- */

/* Counts solutions of b (modified in place, work on a copy), up to `limit`. With rnd != 0 the
 * candidate digits are tried in random order. The first solution found is copied to `out`. */
static int search(Work *w, u8 *b, int limit, int rnd, u8 *out)
{
    u16 rowm[9], colm[9], boxm[9];
    int i, sp = 0, count = 0;

    for (i = 0; i < 9; i++) rowm[i] = colm[i] = boxm[i] = 0;
    for (i = 0; i < 81; i++) {
        if (b[i]) {
            unsigned m = 1u << (b[i] - 1);
            if ((rowm[w->row_of[i]] | colm[w->col_of[i]] | boxm[w->box_of[i]]) & m)
                return 0;   /* givens already conflict */
            rowm[w->row_of[i]] |= m; colm[w->col_of[i]] |= m; boxm[w->box_of[i]] |= m;
        }
    }

    for (;;) {
        /* descend: pick the empty cell with the fewest candidates (MRV) */
        int best = -1, best_n = 10;
        unsigned best_c = 0;
        for (i = 0; i < 81; i++) {
            if (!b[i]) {
                unsigned c = ALL & ~(rowm[w->row_of[i]] | colm[w->col_of[i]] | boxm[w->box_of[i]]);
                int n = popcount9(c);
                if (n < best_n) {
                    best = i; best_c = c; best_n = n;
                    if (n <= 1) break;
                }
            }
        }
        if (best < 0) {
            if (count == 0 && out)
                for (i = 0; i < 81; i++) out[i] = b[i];
            if (++count >= limit) return count;
        } else if (best_n > 0) {
            w->stk_idx[sp] = best;
            w->stk_cand[sp] = best_c;
            sp++;
        }

        /* advance: try the next digit at the top of the stack, popping exhausted cells */
        for (;;) {
            int idx, d;
            unsigned c, m;
            if (sp == 0) return count;
            idx = w->stk_idx[sp - 1];
            if (b[idx]) {
                m = 1u << (b[idx] - 1);
                rowm[w->row_of[idx]] &= ~m; colm[w->col_of[idx]] &= ~m; boxm[w->box_of[idx]] &= ~m;
                b[idx] = 0;
            }
            c = w->stk_cand[sp - 1];
            if (!c) { sp--; continue; }
            if (rnd) {
                int k = (int)w->rng(popcount9(c));
                unsigned t = c;
                while (k--) t &= t - 1;
                d = lowest_digit(t);
            } else {
                d = lowest_digit(c);
            }
            m = 1u << (d - 1);
            w->stk_cand[sp - 1] = c & ~m;
            b[idx] = d;
            rowm[w->row_of[idx]] |= m; colm[w->col_of[idx]] |= m; boxm[w->box_of[idx]] |= m;
            break;
        }
    }
}

static int has_unique_solution(Work *w, const u8 *puz)
{
    int i;
    for (i = 0; i < 81; i++) w->tmp[i] = puz[i];
    return search(w, w->tmp, 2, 0, 0) == 1;
}

/* ---- human-technique rater (techniques.py), bitmask candidates ---- */

static void rate_place(Work *w, int idx, int d)
{
    unsigned m = ~(1u << (d - 1));
    int k;
    const u8 *ur = w->units[w->row_of[idx]], *uc = w->units[9 + w->col_of[idx]],
             *ub = w->units[18 + w->box_of[idx]];
    w->rb[idx] = d;
    w->cand[idx] = 0;
    for (k = 0; k < 9; k++) {
        w->cand[ur[k]] &= m; w->cand[uc[k]] &= m; w->cand[ub[k]] &= m;
    }
}

static int naked_single(Work *w)
{
    int i;
    for (i = 0; i < 81; i++)
        if (!w->rb[i] && popcount9(w->cand[i]) == 1) {
            rate_place(w, i, lowest_digit(w->cand[i]));
            return 1;
        }
    return 0;
}

static int hidden_single(Work *w)
{
    int u, d, k;
    for (u = 0; u < 27; u++)
        for (d = 1; d <= 9; d++) {
            unsigned m = 1u << (d - 1);
            int n = 0, spot = -1;
            for (k = 0; k < 9; k++) {
                int i = w->units[u][k];
                if (!w->rb[i] && (w->cand[i] & m)) { n++; spot = i; }
            }
            if (n == 1) { rate_place(w, spot, d); return 1; }
        }
    return 0;
}

/* pointing pair/triple: a digit confined to one row/col inside a box is removed from the rest of that line */
static int pointing(Work *w)
{
    int b, d, k, changed = 0;
    for (b = 0; b < 9; b++)
        for (d = 1; d <= 9; d++) {
            unsigned m = 1u << (d - 1);
            int n = 0, r = -1, c = -1, same_r = 1, same_c = 1;
            const u8 *box = w->units[18 + b];
            for (k = 0; k < 9; k++) {
                int i = box[k];
                if (w->cand[i] & m) {
                    if (n == 0) { r = w->row_of[i]; c = w->col_of[i]; }
                    else { if (w->row_of[i] != r) same_r = 0; if (w->col_of[i] != c) same_c = 0; }
                    n++;
                }
            }
            if (n < 2 || n > 3) continue;
            if (same_r)
                for (k = 0; k < 9; k++) {
                    int i = w->units[r][k];
                    if (w->box_of[i] != b && (w->cand[i] & m)) { w->cand[i] &= ~m; changed = 1; }
                }
            if (same_c)
                for (k = 0; k < 9; k++) {
                    int i = w->units[9 + c][k];
                    if (w->box_of[i] != b && (w->cand[i] & m)) { w->cand[i] &= ~m; changed = 1; }
                }
        }
    return changed;
}

static int box_line(Work *w)
{
    int u, d, k, changed = 0;
    for (u = 0; u < 18; u++)
        for (d = 1; d <= 9; d++) {
            unsigned m = 1u << (d - 1);
            int n = 0, bx = -1, same = 1;
            for (k = 0; k < 9; k++) {
                int i = w->units[u][k];
                if (w->cand[i] & m) {
                    if (n == 0) bx = w->box_of[i]; else if (w->box_of[i] != bx) same = 0;
                    n++;
                }
            }
            if (n < 2 || n > 3 || !same) continue;
            for (k = 0; k < 9; k++) {
                int i = w->units[18 + bx][k];
                int in_unit = (u < 9) ? (w->row_of[i] == u) : (w->col_of[i] == u - 9);
                if (!in_unit && (w->cand[i] & m)) { w->cand[i] &= ~m; changed = 1; }
            }
        }
    return changed;
}

static int naked_pair(Work *w)
{
    int u, a, b, k, changed = 0;
    for (u = 0; u < 27; u++) {
        const u8 *un = w->units[u];
        for (a = 0; a < 9; a++) {
            unsigned ca = w->cand[un[a]];
            if (popcount9(ca) != 2) continue;
            for (b = a + 1; b < 9; b++) {
                if (w->cand[un[b]] != ca) continue;
                for (k = 0; k < 9; k++)
                    if (k != a && k != b && (w->cand[un[k]] & ca)) {
                        w->cand[un[k]] &= ~ca;
                        changed = 1;
                    }
            }
        }
    }
    return changed;
}

static int hidden_pair(Work *w)
{
    int u, d1, d2, k, changed = 0;
    for (u = 0; u < 27; u++) {
        const u8 *un = w->units[u];
        unsigned pos[10];   /* bitmask of unit positions holding each digit */
        for (d1 = 1; d1 <= 9; d1++) {
            unsigned m = 1u << (d1 - 1);
            pos[d1] = 0;
            for (k = 0; k < 9; k++)
                if (w->cand[un[k]] & m) pos[d1] |= 1u << k;
        }
        for (d1 = 1; d1 <= 9; d1++) {
            if (popcount9(pos[d1]) != 2) continue;
            for (d2 = d1 + 1; d2 <= 9; d2++) {
                unsigned keep;
                if (pos[d2] != pos[d1]) continue;
                keep = (1u << (d1 - 1)) | (1u << (d2 - 1));
                for (k = 0; k < 9; k++)
                    if ((pos[d1] >> k) & 1) {
                        int i = un[k];
                        if (w->cand[i] & ~keep) { w->cand[i] &= keep; changed = 1; }
                    }
            }
        }
    }
    return changed;
}

/* Returns 1 if puz is solvable by pure logic using techniques up to max_tier. */
static int solvable_within(Work *w, const u8 *puz, int max_tier)
{
    int i, k, steps;
    for (i = 0; i < 81; i++) {
        w->rb[i] = puz[i];
        w->cand[i] = puz[i] ? 0 : ALL;
    }
    for (i = 0; i < 81; i++)
        if (puz[i]) {
            unsigned m = ~(1u << (puz[i] - 1));
            const u8 *ur = w->units[w->row_of[i]], *uc = w->units[9 + w->col_of[i]],
                     *ub = w->units[18 + w->box_of[i]];
            for (k = 0; k < 9; k++) {
                w->cand[ur[k]] &= m; w->cand[uc[k]] &= m; w->cand[ub[k]] &= m;
            }
        }

    for (steps = 0; steps < 2000; steps++) {
        int full = 1;
        for (i = 0; i < 81; i++) if (!w->rb[i]) { full = 0; break; }
        if (full) return 1;
        if (naked_single(w) || hidden_single(w)) continue;
        if (max_tier >= TIER_POINTING && (pointing(w) || box_line(w))) continue;
        if (max_tier >= TIER_PAIR && (naked_pair(w) || hidden_pair(w))) continue;
        return 0;
    }
    return 0;
}

/* ---- generator (generate.py) ---- */

static int clue_count(const u8 *p)
{
    int i, n = 0;
    for (i = 0; i < 81; i++) if (p[i]) n++;
    return n;
}

/* Clue-pattern symmetry, chosen at random per puzzle (the game's own banks all use SYM_ROT180;
 * mixing them makes generated puzzles look less uniform). */
enum { SYM_ROT180, SYM_MIRROR_H, SYM_MIRROR_V, SYM_DIAG, SYM_ANTIDIAG, SYM_NONE, SYM_COUNT };

static int sym_partner(const Work *w, int idx, int sym)
{
    int r = w->row_of[idx], c = w->col_of[idx];
    switch (sym) {
    case SYM_ROT180:   return 80 - idx;
    case SYM_MIRROR_H: return r * 9 + (8 - c);          /* left <-> right */
    case SYM_MIRROR_V: return (8 - r) * 9 + c;          /* top <-> bottom */
    case SYM_DIAG:     return c * 9 + r;                /* transpose */
    case SYM_ANTIDIAG: return (8 - c) * 9 + (8 - r);
    default:           return idx;                      /* no symmetry: single cells */
    }
}

static void dig_to_target(Work *w, int target, int sym)
{
    int i;
    for (i = 0; i < 81; i++) { w->puz[i] = w->sol[i]; w->order[i] = i; }
    for (i = 80; i > 0; i--) {                      /* Fisher-Yates */
        int j = (int)w->rng(i + 1);
        u8 t = w->order[i]; w->order[i] = w->order[j]; w->order[j] = t;
    }
    for (i = 0; i < 81; i++) {
        int idx = w->order[i], partner = sym_partner(w, idx, sym);
        u8 save_a, save_b = 0;
        if (clue_count(w->puz) <= target) break;
        if (!w->puz[idx]) continue;
        save_a = w->puz[idx];
        w->puz[idx] = 0;
        if (partner != idx && w->puz[partner]) { save_b = w->puz[partner]; w->puz[partner] = 0; }
        if (!has_unique_solution(w, w->puz)) {
            w->puz[idx] = save_a;
            if (save_b) w->puz[partner] = save_b;
        }
    }
}

/* difficulty: 0 otegaru, 1 easy, 2 normal, 3 hard (ctx+4 in the game). Fills w->puz / w->sol. */
int sgen_generate(Work *w, int difficulty, int max_attempts)
{
    int lo, hi, tier, attempt, need_beyond_singles;
    switch (difficulty) {   /* clue ranges / tiers calibrated from the game's own banks */
    case 0:  lo = 38; hi = 40; tier = TIER_SINGLE; break;
    case 1:  lo = 21; hi = 39; tier = TIER_SINGLE; break;
    case 2:  lo = 20; hi = 29; tier = TIER_SINGLE; break;
    default: lo = 20; hi = 28; tier = TIER_PAIR;   break;
    }
    build_tables(w);
    /* The real "hard" bank needs pointing/pair techniques ~58% of the time (calibrate.py); the
     * tier is only an upper bound, so explicitly ask for a non-singles puzzle that often. */
    need_beyond_singles = (difficulty == 3) && w->rng(100) < 58;
    for (attempt = 1; attempt <= max_attempts; attempt++) {
        int i, target;
        for (i = 0; i < 81; i++) w->tmp[i] = 0;
        if (search(w, w->tmp, 1, 1, w->sol) != 1) continue;
        target = lo + (int)w->rng(hi - lo + 1);
        dig_to_target(w, target, (int)w->rng(SYM_COUNT));
        if (clue_count(w->puz) > hi + 2) continue;
        if (!solvable_within(w, w->puz, tier)) continue;
        if (need_beyond_singles && solvable_within(w, w->puz, TIER_SINGLE)) continue;
        return attempt;
    }
    return 0;
}

static void pack_nibbles(u8 *dst, const u8 *cells)
{
    int i;
    for (i = 0; i < 41; i++) dst[i] = 0;
    for (i = 0; i < 81; i++) {
        if (i & 1) dst[i >> 1] |= cells[i] & 0xF;
        else       dst[i >> 1] |= (cells[i] & 0xF) << 4;
    }
}

/* Overwrites the given/solution grids of a 92-byte record; header (index/type/flags) is kept. */
void sgen_write_record(Work *w, u8 *record)
{
    pack_nibbles(record + 7, w->puz);
    pack_nibbles(record + 48, w->sol);
}

/* Rebuilds w->puz / w->sol from a given grid (used to restore a saved random puzzle).
 * Returns 1 if the grid has exactly one solution. */
int sgen_solve(Work *w, const u8 *puz)
{
    int i;
    build_tables(w);
    for (i = 0; i < 81; i++) w->puz[i] = w->tmp[i] = puz[i];
    return search(w, w->tmp, 2, 0, w->sol) == 1;
}
