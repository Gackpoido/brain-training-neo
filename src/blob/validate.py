import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'prototype'))
import core, techniques as tech
P = {0: (38, 40, tech.TIER_SINGLE), 1: (21, 39, tech.TIER_SINGLE), 2: (20, 29, tech.TIER_SINGLE), 3: (20, 28, tech.TIER_PAIR)}
bad = 0; n = 0; tiers = {}
for line in open(sys.argv[1]):
    if line.startswith('sizeof'): continue
    d, p, s, att = line.split(); d = int(d); att = int(att)
    puz = [int(c) for c in p]; sol = [int(c) for c in s]; n += 1
    lo, hi, mt = P[d]
    errs = []
    if att == 0: errs.append('generation failed')
    if not all(core.Masks(sol).candidates(i) == 0 for i in range(81)) or sorted(sol[:9]) != list(range(1, 10)): pass
    if core.solve_unique(sol) != sol or 0 in sol: errs.append('bad solution grid')
    if any(puz[i] and puz[i] != sol[i] for i in range(81)): errs.append('givens != solution')
    if not core.has_unique_solution(puz): errs.append('not unique')
    if core.solve_unique(puz) != sol: errs.append('solution mismatch')
    clues = sum(1 for v in puz if v)
    if clues > hi + 2: errs.append(f'clues {clues} > {hi+2}')
    r = tech.rate_difficulty(puz)
    if not r.solved or r.max_tier > mt: errs.append(f'tier {r.max_tier} > {mt}')
    tiers.setdefault(d, {}).setdefault(r.max_tier, 0); tiers[d][r.max_tier] += 1
    if errs: bad += 1; print('BAD', d, p, errs)
print(f'{n} puzzles, {bad} bad; tier distribution per difficulty: {tiers}')
