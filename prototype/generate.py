"""Generates random Sudoku puzzles matching the difficulty profile measured
from the real game's own puzzle banks (see calibrate.py):

  otegaru: ~39 clues,      solvable with singles only
  easy:    21-39 clues,    solvable with singles only
  normal:  20-29 clues,    solvable with singles only
  hard:    20-28 clues,    singles/pointing-pairs/pairs (never triples+)

Every generated puzzle is guaranteed to have a UNIQUE solution and to be
solvable via pure logic (no guessing/backtracking) within the target
technique tier.
"""
import random
import time

import core
import techniques as tech

DIFFICULTY_PARAMS = {
    "otegaru": {"clue_range": (38, 40), "max_tier": tech.TIER_SINGLE},
    "easy":    {"clue_range": (21, 39), "max_tier": tech.TIER_SINGLE},
    "normal":  {"clue_range": (20, 29), "max_tier": tech.TIER_SINGLE},
    "hard":    {"clue_range": (20, 28), "max_tier": tech.TIER_PAIR},
}


def dig_to_target(solution, target_clues, rng):
    puzzle = list(solution)
    order = list(range(81))
    rng.shuffle(order)

    def clue_count():
        return sum(1 for v in puzzle if v != 0)

    for idx in order:
        if clue_count() <= target_clues:
            break
        if puzzle[idx] == 0:
            continue
        partner = 80 - idx
        removed = [idx]
        saved = {idx: puzzle[idx]}
        puzzle[idx] = 0
        if partner != idx and puzzle[partner] != 0:
            saved[partner] = puzzle[partner]
            puzzle[partner] = 0
            removed.append(partner)

        if not core.has_unique_solution(puzzle):
            for i in removed:
                puzzle[i] = saved[i]

    return puzzle


def generate_puzzle(difficulty, rng=None, max_attempts=300):
    rng = rng or random.Random()
    params = DIFFICULTY_PARAMS[difficulty]
    clue_lo, clue_hi = params["clue_range"]
    max_tier = params["max_tier"]

    for attempt in range(max_attempts):
        solution = core.generate_full_solution(rng)
        target_clues = rng.randint(clue_lo, clue_hi)
        puzzle = dig_to_target(solution, target_clues, rng)
        actual_clues = sum(1 for v in puzzle if v != 0)
        if actual_clues > clue_hi + 2:
            continue
        result = tech.rate_difficulty(puzzle)
        if result.solved and result.max_tier <= max_tier:
            return puzzle, solution, result, actual_clues, attempt + 1

    raise RuntimeError(f"could not generate a '{difficulty}' puzzle after {max_attempts} attempts")


if __name__ == "__main__":
    rng = random.Random(12345)
    for difficulty in ["otegaru", "easy", "normal", "hard"]:
        t0 = time.time()
        puzzle, solution, result, clues, attempts = generate_puzzle(difficulty, rng)
        dt = time.time() - t0
        print(f"\n=== {difficulty} === clues={clues} tier={tech.TIER_NAMES[result.max_tier]} "
              f"attempts={attempts} time={dt:.2f}s")
        core.print_grid(puzzle)
