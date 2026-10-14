@ Difficulty screen init (init_sudoku_difficulty_screen): registers an extra touch region, id 8, at
@ the empty "Read" slot (x=224, y=128, 32x64) of widget group ctx+0x290 (r4 = screen ctx).
@ Replaces `mov r0,#2` at 0x0204b34c with `bl` here; replays it and the following `bl 0x0208f510`,
@ then returns after them (0x0204b354). Stack args of register_touch_region: [sp]=y, [sp+4]=w, [sp+8]=h.
.arm
.global _start
_start:
    mov r0, #0x80           @ y = 128
    str r0, [sp]
    mov r0, #0x20           @ w = 32
    str r0, [sp, #4]
    mov r0, #0x40           @ h = 64
    str r0, [sp, #8]
    add r0, r4, #0x290      @ touch-region group
    mov r1, #8              @ id
    mov r2, #0
    mov r3, #0xe0           @ x = 224
    bl REGISTER_TOUCH_REGION
    mov r0, #2              @ replayed original instructions
    bl FUN_0208F510
    b RETURN_POINT
