/* Host test: generate N puzzles per difficulty, print them as "<diff> <puzzle81> <solution81> <attempts>"
 * for validation against the Python reference (validate.py). */
#include <stdio.h>
#include <stdlib.h>
#include "sgen.h"

static unsigned long long state = 0x123456789ULL;
static u32 host_rng(u32 range)
{
    state = state * 6364136223846793005ULL + 1442695040888963407ULL;
    u32 hi = (u32)(state >> 32);
    return range ? (u32)(((unsigned long long)hi * range) >> 32) : hi;
}

int main(int argc, char **argv)
{
    int n = argc > 1 ? atoi(argv[1]) : 20, d, k, i;
    static Work w;
    printf("sizeof(Work)=%zu\n", sizeof(Work));
    w.rng = host_rng;
    for (d = 0; d < 4; d++)
        for (k = 0; k < n; k++) {
            int att = sgen_generate(&w, d, 300);
            printf("%d ", d);
            for (i = 0; i < 81; i++) putchar('0' + w.puz[i]);
            putchar(' ');
            for (i = 0; i < 81; i++) putchar('0' + w.sol[i]);
            printf(" %d\n", att);
        }
    return 0;
}
