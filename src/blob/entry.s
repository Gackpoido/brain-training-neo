@ Blob entry table. The resident call_blob helper (arm9 v21) loads /data/Sudoku/sgen.bin into a heap
@ buffer and calls base+offset with r0, r1 = its two arguments and r2 = blob base.
@ Position independent; returns the C function's result in r0.
.arm
.section .text.entry, "ax"
.global _start
_start:
    b ent_sel               @ +0  difficulty_selector(bank, idx)
    b ent_cont              @ +4  FUN_020437cc(bank, number)
    b ent_menu              @ +8  difficulty pressed (menu ctx)
    b ent_save              @ +12 after pack_cells_into_save_buffer(cells, slots)
    b ent_icon              @ +16 difficulty screen init: draw the dice over the Leer tiles
ent_sel:
    ldr r3, work_off
    add r2, r2, r3          @ Work area = blob base + offset (zero-filled tail of the blob)
    b blob_sel
ent_cont:
    ldr r3, work_off
    add r2, r2, r3
    b blob_cont
ent_menu:
    ldr r3, work_off
    add r2, r2, r3
    b blob_menu
ent_save:
    ldr r3, work_off
    add r2, r2, r3
    b blob_save
ent_icon:
    adr r0, button_tiles     @ PC-relative: keeps the blob position independent
    b blob_icon
work_off:
    .word work_area - _start
.balign 4
button_tiles:                @ 4 VRAM tile rows x 8 tiles (Stay sheet cols 16..23): the dice button.
    .incbin "button_tiles.bin"  @ zero placeholder; build.py fills it from the user's ROM (graphics/make_dice.py)

.section .work, "aw"
.balign 8
work_area:
    .space 2048
