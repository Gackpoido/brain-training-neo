"""Bitmask-based Sudoku solving/generation primitives.

Board representation: list of 81 ints, 0 = empty, 1-9 = digit, row-major
(index = row*9+col). Candidate sets are represented as 9-bit masks (bit
d-1 set => digit d is a candidate).
"""
import random

BOX_OF = [(r // 3) * 3 + (c // 3) for r in range(9) for c in range(9)]
PEERS = []  # for each cell, list of the other 20 cells sharing a row/col/box
UNITS = []  # for each cell, the three units (row, col, box) it belongs to, each a list of 9 indices

ALL_DIGITS_MASK = 0x1FF  # bits 0..8 => digits 1..9


def _build_units_and_peers():
    rows = [[r * 9 + c for c in range(9)] for r in range(9)]
    cols = [[r * 9 + c for r in range(9)] for c in range(9)]
    boxes = [[] for _ in range(9)]
    for idx in range(81):
        boxes[BOX_OF[idx]].append(idx)

    for idx in range(81):
        r, c, b = idx // 9, idx % 9, BOX_OF[idx]
        units = [rows[r], cols[c], boxes[b]]
        UNITS.append(units)
        peers = set()
        for u in units:
            peers.update(u)
        peers.discard(idx)
        PEERS.append(sorted(peers))


_build_units_and_peers()


def bit(d):
    return 1 << (d - 1)


def digit_of_bit(m):
    return m.bit_length()


def popcount(m):
    return bin(m).count("1")


class Masks:
    """Row/col/box used-digit bitmasks, kept in sync with a board array."""

    __slots__ = ("row", "col", "box")

    def __init__(self, board=None):
        self.row = [0] * 9
        self.col = [0] * 9
        self.box = [0] * 9
        if board:
            for idx, v in enumerate(board):
                if v:
                    self.place(idx, v)

    def candidates(self, idx):
        r, c, b = idx // 9, idx % 9, BOX_OF[idx]
        used = self.row[r] | self.col[c] | self.box[b]
        return ALL_DIGITS_MASK & ~used

    def place(self, idx, d):
        r, c, b = idx // 9, idx % 9, BOX_OF[idx]
        m = bit(d)
        self.row[r] |= m
        self.col[c] |= m
        self.box[b] |= m

    def remove(self, idx, d):
        r, c, b = idx // 9, idx % 9, BOX_OF[idx]
        m = ~bit(d)
        self.row[r] &= m
        self.col[c] &= m
        self.box[b] &= m


def generate_full_solution(rng=None):
    """Randomized backtracking with MRV heuristic. Returns a completed 81-cell board."""
    rng = rng or random.Random()
    board = [0] * 81
    masks = Masks()

    def backtrack():
        best_idx, best_cands, best_count = -1, 0, 10
        for idx in range(81):
            if board[idx] == 0:
                cands = masks.candidates(idx)
                cnt = popcount(cands)
                if cnt == 0:
                    return False
                if cnt < best_count:
                    best_idx, best_cands, best_count = idx, cands, cnt
                    if cnt == 1:
                        break
        if best_idx == -1:
            return True  # solved

        digits = [d for d in range(1, 10) if best_cands & bit(d)]
        rng.shuffle(digits)
        for d in digits:
            board[best_idx] = d
            masks.place(best_idx, d)
            if backtrack():
                return True
            masks.remove(best_idx, d)
            board[best_idx] = 0
        return False

    ok = backtrack()
    assert ok, "unexpected failure generating a full grid"
    return board


def count_solutions(board, limit=2):
    """Counts solutions of a (possibly partial) board, stopping early at `limit`."""
    board = list(board)
    masks = Masks(board)
    count = 0

    def backtrack():
        nonlocal count
        best_idx, best_cands, best_count = -1, 0, 10
        for idx in range(81):
            if board[idx] == 0:
                cands = masks.candidates(idx)
                cnt = popcount(cands)
                if cnt == 0:
                    return
                if cnt < best_count:
                    best_idx, best_cands, best_count = idx, cands, cnt
                    if cnt == 1:
                        break
        if best_idx == -1:
            count += 1
            return
        for d in range(1, 10):
            if best_cands & bit(d):
                board[best_idx] = d
                masks.place(best_idx, d)
                backtrack()
                masks.remove(best_idx, d)
                board[best_idx] = 0
                if count >= limit:
                    return

    backtrack()
    return count


def has_unique_solution(board):
    return count_solutions(board, limit=2) == 1


def solve_unique(board):
    """Solves a board known/assumed to have a unique solution. Returns the solution or None."""
    board = list(board)
    masks = Masks(board)

    def backtrack():
        best_idx, best_cands, best_count = -1, 0, 10
        for idx in range(81):
            if board[idx] == 0:
                cands = masks.candidates(idx)
                cnt = popcount(cands)
                if cnt == 0:
                    return False
                if cnt < best_count:
                    best_idx, best_cands, best_count = idx, cands, cnt
                    if cnt == 1:
                        break
        if best_idx == -1:
            return True
        for d in range(1, 10):
            if best_cands & bit(d):
                board[best_idx] = d
                masks.place(best_idx, d)
                if backtrack():
                    return True
                masks.remove(best_idx, d)
                board[best_idx] = 0
        return False

    if backtrack():
        return board
    return None


def print_grid(board):
    for r in range(9):
        row = board[r * 9:(r + 1) * 9]
        print(' '.join(str(v) if v else '.' for v in row))


def dig_holes(solution, rng=None, symmetric=True, stop_check=None):
    """Removes cells from a complete solution one at a time (in random order),
    keeping the puzzle uniquely solvable at every step.

    `stop_check(puzzle) -> bool`: optional callback consulted after each
    successful removal; digging stops as soon as it returns True (used to
    stop once a target difficulty tier has been reached).

    Returns the resulting puzzle (0 = blank cell).
    """
    rng = rng or random.Random()
    puzzle = list(solution)
    order = list(range(81))
    rng.shuffle(order)

    for idx in order:
        if puzzle[idx] == 0:
            continue
        partner = 80 - idx  # 180-degree rotational partner
        removed = [idx]
        saved = {idx: puzzle[idx]}
        puzzle[idx] = 0
        if symmetric and partner != idx and puzzle[partner] != 0:
            saved[partner] = puzzle[partner]
            puzzle[partner] = 0
            removed.append(partner)

        if has_unique_solution(puzzle):
            if stop_check is not None and stop_check(puzzle):
                return puzzle
        else:
            for i in removed:
                puzzle[i] = saved[i]

    return puzzle
