.arm
.global _start
_start:
    @ Copy the right-hand BG strip's tile rows 0-8 (Atras button drop shadow, engine B BG1,
    @ char base 0xC000) onto tile rows 15-23 (the Leer slot, exactly 120px lower) every frame.
    ldr r0, =0x0620c000
    add r1, r0, #0x780
    mov r2, #0x480
copy:
    ldmia r0!, {r3, r12}
    stmia r1!, {r3, r12}
    subs r2, r2, #8
    bne copy
    mov r0, r6
    b RETURN_POINT
