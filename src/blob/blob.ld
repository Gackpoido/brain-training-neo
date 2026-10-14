ENTRY(_start)
SECTIONS
{
    . = BASE;
    .text : { *(.text.entry) *(.text*) *(.rodata*) *(.data*) *(.bss*) *(COMMON) *(.work) }
    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.attributes) *(.comment) }
}
