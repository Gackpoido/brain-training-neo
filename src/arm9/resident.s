@ Resident hook code. Lives in the body of difficulty_selector (0x020438e8, 308 bytes incl. its
@ literal pool), whose logic moved into the sgen.bin blob (blob_sel).
.arm
.global _start
.equ E_SEL,  0
.equ E_CONT, 4
.equ E_MENU, 8
.equ E_SAVE, 12
.equ E_ICON, 16

_start:                         @ difficulty_selector(bank, idx) -> blob_sel
    mov r2, #E_SEL
    b call_blob

@ call_blob(a0, a1, entry_offset): load /data/Sudoku/sgen.bin into a heap buffer, run
@ blob+entry_offset(a0, a1, base) and free it. Runs outside any file-loader callback, so the blob
@ may itself use the game's file functions. Returns the blob's r0.
.global call_blob
call_blob:
    push {r4-r8, lr}
    mov r4, r0
    mov r5, r1
    mov r6, r2
    ldr r0, path_lit
    bl GET_FILE_SIZE
    mov r7, r0
    bl ALLOCATE_MEMORY
    movs r8, r0
    beq 1f
    mov r1, r8
    mov r2, r7
    ldr r0, path_lit
    mov r3, #0
    bl LOAD_FILE_TO_BUFFER
    bl DC_FLUSH_ALL             @ write the loaded code back to RAM...
    mov r0, #0
    mcr p15, 0, r0, c7, c5, 0   @ ...and drop stale I-cache lines
    mov r0, r4
    mov r1, r5
    mov r2, r8
    add r12, r8, r6
    blx r12
    mov r4, r0
    mov r0, r8
    bl FREE_MEMORY
    mov r0, r4
1:  pop {r4-r8, pc}

@ Difficulty screen, `bl init_sudoku_puzzle_bank` (r0 = bank, r1 = difficulty, r6 = menu ctx).
.global h_menu
h_menu:
    push {r4, lr}
    bl INIT_PUZZLE_BANK
    mov r0, r6
    mov r2, #E_MENU
    bl call_blob
    pop {r4, pc}

@ FUN_020492f4 (save & exit), `bl pack_cells_into_save_buffer` (r0 = cells, r1 = save slots).
.global h_save
h_save:
    push {r0, r1, r4, lr}
    bl PACK_CELLS
    pop {r0, r1}
    mov r2, #E_SAVE
    bl call_blob
    pop {r4, pc}

@ Screen switch (FUN_0205060c -> FUN_0204e3b0(new_screen)): in random mode the puzzle picker
@ (0x81) is replaced by the difficulty screen (0x80).
.global h_screen
h_screen:
    cmp r0, #0x81
    bne SCREEN_SWITCH
    ldr r12, flag_lit
    ldr r12, [r12]
    cmp r12, #0
    movne r0, #0x80
    ldrne r12, req_lit
    strne r0, [r12]
    b SCREEN_SWITCH

@ FUN_02043744(bank) = stamp/record id of the current puzzle: -1 for random puzzles (like Download
@ Play puzzles), so no stamp or record is written. First instruction of FUN_02043744 jumps here.
.global h_stamp
h_stamp:
    ldrb r1, [r0, #0x24b]
    cmp r1, #0xa5
    mvneq r0, #0
    bxeq lr
    ldr r3, [r0, #8]            @ replayed first instruction
    b STAMP_ORIG_NEXT

@ Difficulty screen init, `bl set_subslot_state(ctx,1,1,0x380)` right after the Stay tiles were
@ copied to OBJ VRAM: let the blob overwrite the Leer button tiles with the dice graphic.
.global h_icon
h_icon:
    push {r4, lr}
    bl SET_SUBSLOT_STATE
    mov r2, #E_ICON
    bl call_blob
    pop {r4, pc}

path_lit: .word BLOB_PATH
flag_lit: .word RANDOM_FLAG
req_lit:  .word SCREEN_REQUEST
