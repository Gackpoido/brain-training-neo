"""Human-technique Sudoku solver, used to rate a puzzle's real difficulty
(which logic techniques are required to solve it without guessing/backtracking)
rather than just counting given clues.

Tiers, roughly in increasing difficulty (matches common human-solving guides):
  1 SINGLE   - naked single / hidden single
  2 POINTING - pointing pair/triple, box-line reduction
  3 PAIR     - naked pair, hidden pair
  4 TRIPLE   - naked triple, hidden triple
  X (UNSOLVED) - solver got stuck: would require guessing or a technique
                 beyond this set (X-wing and above). Puzzles rated X are
                 rejected by the generator.
"""
from core import UNITS, BOX_OF

TIER_SINGLE = 1
TIER_POINTING = 2
TIER_PAIR = 3
TIER_TRIPLE = 4
TIER_UNSOLVED = 99

TIER_NAMES = {
    TIER_SINGLE: "SINGLE",
    TIER_POINTING: "POINTING",
    TIER_PAIR: "PAIR",
    TIER_TRIPLE: "TRIPLE",
    TIER_UNSOLVED: "UNSOLVED (needs guessing / advanced technique)",
}

ROWS = [list(range(r * 9, r * 9 + 9)) for r in range(9)]
COLS = [list(range(c, 81, 9)) for c in range(9)]
BOXES = [[i for i in range(81) if BOX_OF[i] == b] for b in range(9)]
ALL_UNITS = ROWS + COLS + BOXES


class TechniqueResult:
    def __init__(self, solved, max_tier, step_count, tier_counts):
        self.solved = solved
        self.max_tier = max_tier if solved else TIER_UNSOLVED
        self.step_count = step_count
        self.tier_counts = tier_counts  # {tier: count}

    def __repr__(self):
        name = TIER_NAMES.get(self.max_tier, self.max_tier)
        return f"TechniqueResult(solved={self.solved}, tier={name}, steps={self.step_count})"


def _init_candidates(board):
    cands = [set() if board[i] else set(range(1, 10)) for i in range(81)]
    for i in range(81):
        if board[i]:
            continue
        for unit in UNITS[i]:
            for j in unit:
                if board[j]:
                    cands[i].discard(board[j])
    return cands


def _place(board, cands, idx, digit):
    board[idx] = digit
    cands[idx] = set()
    for j in UNITS_FLAT[idx]:
        cands[j].discard(digit)


UNITS_FLAT = UNITS  # UNITS[i] already gives the 3 units (each a list of 9 idx) containing i


def _place_v2(board, cands, idx, digit):
    board[idx] = digit
    cands[idx] = set()
    for unit in UNITS[idx]:
        for j in unit:
            if j != idx:
                cands[j].discard(digit)


def _naked_single(board, cands):
    for i in range(81):
        if board[i] == 0 and len(cands[i]) == 1:
            _place_v2(board, cands, i, next(iter(cands[i])))
            return True
    return False


def _hidden_single(board, cands):
    for unit in ALL_UNITS:
        for d in range(1, 10):
            spots = [i for i in unit if board[i] == 0 and d in cands[i]]
            if len(spots) == 1:
                _place_v2(board, cands, spots[0], d)
                return True
    return False


def _naked_pair(cands):
    changed = False
    for unit in ALL_UNITS:
        empties = [i for i in unit if len(cands[i]) == 2]
        for a in range(len(empties)):
            for b in range(a + 1, len(empties)):
                i, j = empties[a], empties[b]
                if cands[i] == cands[j]:
                    for k in unit:
                        if k != i and k != j and cands[k] & cands[i]:
                            before = len(cands[k])
                            cands[k] -= cands[i]
                            if len(cands[k]) != before:
                                changed = True
    return changed


def _hidden_pair(cands):
    changed = False
    for unit in ALL_UNITS:
        empties = [i for i in unit if cands[i]]
        for d1 in range(1, 10):
            spots1 = [i for i in empties if d1 in cands[i]]
            if len(spots1) != 2:
                continue
            for d2 in range(d1 + 1, 10):
                spots2 = [i for i in empties if d2 in cands[i]]
                if spots2 == spots1:
                    for i in spots1:
                        before = len(cands[i])
                        cands[i] &= {d1, d2}
                        if len(cands[i]) != before:
                            changed = True
    return changed


def _naked_triple(cands):
    changed = False
    for unit in ALL_UNITS:
        empties = [i for i in unit if 2 <= len(cands[i]) <= 3]
        n = len(empties)
        for a in range(n):
            for b in range(a + 1, n):
                for c in range(b + 1, n):
                    i, j, k = empties[a], empties[b], empties[c]
                    union = cands[i] | cands[j] | cands[k]
                    if len(union) == 3:
                        for m in unit:
                            if m not in (i, j, k) and cands[m] & union:
                                before = len(cands[m])
                                cands[m] -= union
                                if len(cands[m]) != before:
                                    changed = True
    return changed


def _hidden_triple(cands):
    changed = False
    for unit in ALL_UNITS:
        empties = [i for i in unit if cands[i]]
        for d1 in range(1, 10):
            for d2 in range(d1 + 1, 10):
                for d3 in range(d2 + 1, 10):
                    triple = {d1, d2, d3}
                    spots = [i for i in empties if cands[i] & triple]
                    if 2 <= len(spots) <= 3 and len(spots) == len({i for i in spots}):
                        # digits d1,d2,d3 must be confined to exactly these cells
                        union_positions = spots
                        if len(union_positions) == 3:
                            for i in union_positions:
                                before = len(cands[i])
                                cands[i] &= triple
                                if len(cands[i]) != before:
                                    changed = True
    return changed


def _pointing(cands):
    changed = False
    for b, box in enumerate(BOXES):
        for d in range(1, 10):
            spots = [i for i in box if d in cands[i]]
            if 2 <= len(spots) <= 3:
                rows = {i // 9 for i in spots}
                cols = {i % 9 for i in spots}
                if len(rows) == 1:
                    r = next(iter(rows))
                    for i in ROWS[r]:
                        if i not in box and d in cands[i]:
                            cands[i].discard(d)
                            changed = True
                if len(cols) == 1:
                    c = next(iter(cols))
                    for i in COLS[c]:
                        if i not in box and d in cands[i]:
                            cands[i].discard(d)
                            changed = True
    return changed


def _box_line_reduction(cands):
    changed = False
    for unit in ROWS + COLS:
        for d in range(1, 10):
            spots = [i for i in unit if d in cands[i]]
            if 2 <= len(spots) <= 3:
                boxes = {BOX_OF[i] for i in spots}
                if len(boxes) == 1:
                    b = next(iter(boxes))
                    for i in BOXES[b]:
                        if i not in unit and d in cands[i]:
                            cands[i].discard(d)
                            changed = True
    return changed


# techniques in increasing difficulty order; each returns True if it made progress
_TECHNIQUES = [
    (TIER_SINGLE, "naked_single", lambda board, cands: _naked_single(board, cands)),
    (TIER_SINGLE, "hidden_single", lambda board, cands: _hidden_single(board, cands)),
    (TIER_POINTING, "pointing", lambda board, cands: _pointing(cands)),
    (TIER_POINTING, "box_line_reduction", lambda board, cands: _box_line_reduction(cands)),
    (TIER_PAIR, "naked_pair", lambda board, cands: _naked_pair(cands)),
    (TIER_PAIR, "hidden_pair", lambda board, cands: _hidden_pair(cands)),
    (TIER_TRIPLE, "naked_triple", lambda board, cands: _naked_triple(cands)),
    (TIER_TRIPLE, "hidden_triple", lambda board, cands: _hidden_triple(cands)),
]


def rate_difficulty(puzzle, max_steps=2000):
    """Attempts to solve `puzzle` using only human logic techniques.

    Returns a TechniqueResult. If the solver gets stuck before completion,
    `solved` is False and `max_tier` is TIER_UNSOLVED, meaning this puzzle
    would require guessing (backtracking) or a technique beyond this set.
    """
    board = list(puzzle)
    cands = _init_candidates(board)
    max_tier_used = 0
    tier_counts = {}
    steps = 0

    while steps < max_steps:
        if all(board):
            return TechniqueResult(True, max_tier_used, steps, tier_counts)
        progressed = False
        for tier, name, fn in _TECHNIQUES:
            if fn(board, cands):
                progressed = True
                max_tier_used = max(max_tier_used, tier)
                tier_counts[name] = tier_counts.get(name, 0) + 1
                steps += 1
                break
        if not progressed:
            break

    solved = all(board)
    return TechniqueResult(solved, max_tier_used, steps, tier_counts)
