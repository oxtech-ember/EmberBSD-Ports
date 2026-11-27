# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exported as devel/nasm/file-symbols.mk.
#
# NASM has no file prefix map. Each object that NASM assembles keeps the
# absolute build path of its .asm source in an ELF STT_FILE symbol. Linking
# does not use these symbols. Set NASM_STATIC_ARCHIVES to the installed
# static archives, relative to PREFIX, before this file is included;
# post-install then removes the *.asm file symbols from them.

.include "../../mk/bsd.prefs.mk"

.if empty(NASM_STATIC_ARCHIVES)
PKG_FAIL_REASON+= "devel/nasm/file-symbols.mk requires NASM_STATIC_ARCHIVES"
.endif

.if ${OBJECT_FMT} == "ELF" && \
    (${MACHINE_ARCH} == "x86_64" || ${MACHINE_ARCH} == "i386")
.PHONY: nasm-strip-file-symbols
post-install: nasm-strip-file-symbols
nasm-strip-file-symbols:
	cd ${DESTDIR}${PREFIX} && \
	    ${STRIP} --wildcard --strip-symbol='*.asm' ${NASM_STATIC_ARCHIVES}
.endif
