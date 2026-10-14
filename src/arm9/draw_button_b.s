.arm
.global _start
_start:
    @ Leer toggle button, part B: random mode off -> force palette 9 (grey, the game's own "NG"/disabled button look); on -> sequence's own
    @ palette 13 (green). Then draw and continue to the shadow copy.
    ldr r0, =RANDOM_FLAG
    ldr r0, [r0]
    cmp r0, #0
    moveq r0, #9
    streq r0, [r6, #0x280]
    mov r0, r6
    bl FUN_02068ae4
    b LEER_SHADOW
