.arm
.global _start
_start:
    cmp r5, #8
    bne skip_case8
    ldr r1, =RANDOM_FLAG
    ldr r0, [r1]
    eor r0, r0, #1        @ toggle random-puzzle mode (session only, starts off)
    str r0, [r1]
    mov r0, #0x10
    bl FUN_02055bac
    b DEFAULT_LABEL
skip_case8:
    cmp r5, #7
    b ORIGINAL_ADDLS
