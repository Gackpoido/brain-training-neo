import sys
import random
import time
from collections import Counter

import core
import format as fmt
import generate as gen
import techniques as tech

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "out"   # where the generated .dat banks are written
import os
os.makedirs(OUT_DIR, exist_ok=True)

N_PER_DIFFICULTY = 40


def check_solution_valid(cells):
    def valid_group(vals):
        return sorted(vals) == list(range(1, 10))
    for r in range(9):
        if not valid_group(cells[r*9:(r+1)*9]):
            return False
    for c in range(9):
        if not valid_group([cells[r*9+c] for r in range(9)]):
            return False
    for br in range(3):
        for bc in range(3):
            box = [cells[(br*3+i)*9+(bc*3+j)] for i in range(3) for j in range(3)]
            if not valid_group(box):
                return False
    return True


def main():
    rng = random.Random(2024)
    for difficulty in ["otegaru", "easy", "normal", "hard"]:
        t0 = time.time()
        records = []
        tier_counter = Counter()
        clue_counts = []
        total_attempts = 0
        for i in range(N_PER_DIFFICULTY):
            puzzle, solution, result, clues, attempts = gen.generate_puzzle(difficulty, rng)
            records.append((puzzle, solution))
            tier_counter[result.max_tier] += 1
            clue_counts.append(clues)
            total_attempts += attempts

            # sanity: unique solution actually matches, and is a valid latin-square+box solution
            assert core.has_unique_solution(puzzle)
            solved = core.solve_unique(puzzle)
            assert solved == solution
            assert check_solution_valid(solution)
            assert all(g == 0 or g == s for g, s in zip(puzzle, solution))

        dt = time.time() - t0
        out_path = f"{OUT_DIR}/sudoku_problem_{difficulty}_generated.dat"
        fmt.save_dat(out_path, records)

        # round-trip through the exact on-disk format and re-validate
        reloaded = fmt.load_dat(out_path)
        for (index, type_flag, given, solution) in reloaded:
            assert check_solution_valid(solution)
            assert all(g == 0 or g == s for g, s in zip(given, solution))

        print(f"=== {difficulty}: {N_PER_DIFFICULTY} puzzles, {dt:.2f}s total, "
              f"{total_attempts} intentos totales ===")
        print(f"  clues: min={min(clue_counts)} max={max(clue_counts)} mean={sum(clue_counts)/len(clue_counts):.1f}")
        for tier in sorted(tier_counter):
            print(f"  tier {tech.TIER_NAMES[tier]}: {tier_counter[tier]}")
        print(f"  saved and verified on disk: {out_path}")
        print()


if __name__ == "__main__":
    main()
