.arm
.global _start
_start:
    @ Leer toggle button, part A: pick Stay.NANR sequence 5 (pressed) while region id 8 is being
    @ touched, else 4; select it on main-slot 1 / sub-slot 1 and place it at (256,192).
    add r0, r6, #0x290
    bl get_touched_region_id
    cmp r0, #8
    moveq r3, #5
    movne r3, #4
    mov r0, r6
    mov r1, #1
    mov r2, #1
    bl FUN_02069178
    mov r0, #0x100000
    str r0, [r6, #0x258]
    mov r0, #0xc0000
    str r0, [r6, #0x25c]
    b PART_B
