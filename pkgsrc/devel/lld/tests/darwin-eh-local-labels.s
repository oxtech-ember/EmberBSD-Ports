# Adapted from LLVM lld/test/MachO/eh-frame-sdata4.s (Apache-2.0 WITH LLVM-exception).
.globl  _main
_main:
  .space 4
Lfunction2:
  .space 4
Lfunction:
  retq
LmainEnd:

.balign 4
.section __TEXT,__eh_frame
# Although we don't reference this EhFrame symbol directly, we must have at
# least one non-local symbol in this section, otherwise llvm-mc generates bogus
# subtractor relocations.
EhFrame:
LCieHdr:
  .long LCieEnd - LCieStart
LCieStart:
  .long 0           # CIE ID
  .byte 1           # CIE version
  .ascii "zR\0"
  .byte 1           # Code alignment
  .byte 1           # Data alignment
  .byte 1           # RA column
  .byte 1           # Augmentation size
  .byte 0x1b        # FDE pointer encoding (pcrel | sdata4)
  .byte 0xc, 7, 8   # DW_CFA_def_cfa reg7 +8
  .balign 4
LCieEnd:

LFdeHdr:
  .long LFdeEnd - LFdeStart
LFdeStart:
  .long LFdeStart - LCieHdr
  # The next two fields are longs instead of quads because of the sdata4
  # encoding.
  .long Lfunction - .        # Function address
  .long LmainEnd - Lfunction # Function length
  .byte 0
  ## Insert DW_CFA_GNU_args_size to prevent ld64 from creating a compact unwind
  ## entry to replace this FDE. Makes it easier for us to cross-check behavior
  ## across the two linkers (LLD never bothers trying to synthesize compact
  ## unwind if it is not already present).
  .byte 0x2e, 0x10       # DW_CFA_GNU_args_size
  .balign 4
LFdeEnd:

LFde2Hdr:
  .long LFde2End - LFde2Start
LFde2Start:
  .long LFde2Start - LCieHdr
  # The next two fields are longs instead of quads because of the sdata4
  # encoding.
  .long Lfunction2 - .        # Function address
  .long 1 # Function length
  .byte 0
  ## Insert DW_CFA_GNU_args_size to prevent ld64 from creating a compact unwind
  ## entry to replace this FDE. Makes it easier for us to cross-check behavior
  ## across the two linkers (LLD never bothers trying to synthesize compact
  ## unwind if it is not already present).
  .byte 0x2e, 0x10       # DW_CFA_GNU_args_size
  .balign 4
LFde2End:

  .long 0 # terminator

.subsections_via_symbols
