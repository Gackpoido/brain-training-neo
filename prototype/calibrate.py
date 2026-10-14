"""Runs the human-technique solver against the real game puzzles to learn
what technique tiers each in-game difficulty actually requires. This
calibrates the generator's difficulty targets against the real game
instead of guessing thresholds.
"""
import sys
from collections import Counter

import format as fmt
import techniques as tech

# Folder with the game's sudoku_problem_*.dat files (extract your ROM with ndstool -d).
# Usage: python3 calibrate.py <extracted .../data/Sudoku folder>
DAT_DIR = sys.argv[1] if len(sys.argv) > 1 else "Sudoku"

FILES = [
    ("otegaru", "sudoku_problem_otegaru.dat"),
    ("easy", "sudoku_problem_easy.dat"),
    ("normal", "sudoku_problem_normal.dat"),
    ("hard", "sudoku_problem_hard.dat"),
]


def main():
    for label, filename in FILES:
        path = f"{DAT_DIR}/{filename}"
        records = fmt.load_dat(path)
        tier_counter = Counter()
        clue_counts = []
        unsolved = 0
        n_valid = 0
        for index, type_flag, given, solution in records:
            clues = sum(1 for g in given if g != 0)
            # skip records that aren't real complete puzzles (tutorial slots, etc.)
            if solution.count(0) > 0:
                continue
            n_valid += 1
            result = tech.rate_difficulty(given)
            tier_counter[result.max_tier] += 1
            clue_counts.append(clues)
            if not result.solved:
                unsolved += 1

        print(f"\n=== {label} ({filename}) — {n_valid} valid puzzles ===")
        if clue_counts:
            print(f"  clues: min={min(clue_counts)} max={max(clue_counts)} mean={sum(clue_counts)/len(clue_counts):.1f}")
        print(f"  not solvable by logic alone (need guessing): {unsolved}")
        for tier in sorted(tier_counter):
            name = tech.TIER_NAMES.get(tier, tier)
            print(f"  tier {name}: {tier_counter[tier]} puzzles")


if __name__ == "__main__":
    main()
