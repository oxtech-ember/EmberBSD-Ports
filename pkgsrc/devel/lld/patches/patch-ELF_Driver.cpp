$NetBSD$

Recognize the ARM hard-float NetBSD emulation used by the Clang driver.
The ARM backend derives the ELF float ABI from the input attributes.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- ELF/Driver.cpp.orig
+++ ELF/Driver.cpp
@@ -155,7 +155,8 @@
       StringSwitch<std::pair<ELFKind, uint16_t>>(s)
           .Cases({"aarch64elf", "aarch64linux"}, {ELF64LEKind, EM_AARCH64})
           .Cases({"aarch64elfb", "aarch64linuxb"}, {ELF64BEKind, EM_AARCH64})
-          .Cases({"armelf", "armelf_linux_eabi"}, {ELF32LEKind, EM_ARM})
+          .Cases({"armelf", "armelf_linux_eabi", "armelf_nbsd_eabihf"},
+                 {ELF32LEKind, EM_ARM})
           .Cases({"armelfb", "armelfb_linux_eabi"}, {ELF32BEKind, EM_ARM})
           .Case("elf32_x86_64", {ELF32LEKind, EM_X86_64})
           .Cases({"elf32btsmip", "elf32btsmipn32"}, {ELF32BEKind, EM_MIPS})
