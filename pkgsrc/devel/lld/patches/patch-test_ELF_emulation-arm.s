$NetBSD$

Check the NetBSD ARM hard-float emulation and its input ABI flags.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- test/ELF/emulation-arm.s.orig
+++ test/ELF/emulation-arm.s
@@ -1,5 +1,10 @@
 # REQUIRES: arm
 # RUN: llvm-mc -filetype=obj -triple=armv7-unknown-linux %s -o %tarm
+# RUN: llvm-mc -filetype=obj -triple=armv7--netbsdelf-eabihf --defsym=NETBSD_HARD_FLOAT=1 %s -o %tarmhf
+# RUN: ld.lld -m armelf_nbsd_eabihf %tarmhf -o %tarmhf.exe
+# RUN: llvm-readobj --file-headers %tarmhf.exe | FileCheck --check-prefix=ARMHF %s
+# RUN: ld.lld -m armelf_nbsd_eabihf %tarm -o %tarmbase.exe
+# RUN: llvm-readobj --file-headers %tarmbase.exe | FileCheck --check-prefix=ARM %s
 # RUN: ld.lld -m armelf %tarm -o %t2arm
 # RUN: llvm-readobj --file-headers %t2arm | FileCheck --check-prefix=ARM %s
 # RUN: ld.lld -m armelf_linux_eabi %tarm -o %t3arm
@@ -81,5 +86,15 @@
 # ARMEB8-NEXT:     0x4000000
 # ARMEB8-NEXT:   ]
 
+# ARMHF: Class: 32-bit
+# ARMHF: DataEncoding: LittleEndian
+# ARMHF: OS/ABI: SystemV
+# ARMHF: Machine: EM_ARM
+# ARMHF: Flags [ (0x5000400)
+
+.ifdef NETBSD_HARD_FLOAT
+.eabi_attribute 28, 1
+.endif
+
 .globl _start
 _start:
