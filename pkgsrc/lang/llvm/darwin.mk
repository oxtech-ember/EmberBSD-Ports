# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# The SDK producer supplies its qualified tool or an explicit scoped seed.
.if !defined(EMBERBSD_LLVM_DARWIN_MK)
EMBERBSD_LLVM_DARWIN_MK= yes
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes"
.if ${EMBERBSD_DARWIN_TOOL_PHASE:Ufull} == "initial"
# The finite SDK operation builds tools with selected ar/ranlib, not a package.
CMAKE_CONFIGURE_ARGS.Darwin+= -DLLVM_DARWIN_ARCHIVE_TOOL:STRING=ar
CMAKE_CONFIGURE_ARGS.Darwin+= -DLLVM_BUILD_LLVM_DYLIB:BOOL=OFF -DLLVM_LINK_LLVM_DYLIB:BOOL=OFF
.elif ${EMBERBSD_DARWIN_TOOL_PHASE:Ufull} != "full"
PKG_FAIL_REASON+= "EMBERBSD_DARWIN_TOOL_PHASE must be initial or full"
.else
.if empty(EMBERBSD_DARWIN_LIBTOOL:M/*) || !exists(${EMBERBSD_DARWIN_LIBTOOL})
PKG_FAIL_REASON+= "EMBERBSD_DARWIN_LIBTOOL must select an existing absolute Darwin archive executable"
.else
_EMBERBSD_DARWIN_LIBTOOL_EXECUTABLE!= if test -f ${EMBERBSD_DARWIN_LIBTOOL:Q} && \
    test -x ${EMBERBSD_DARWIN_LIBTOOL:Q}; then echo yes; else echo no; fi
.if ${_EMBERBSD_DARWIN_LIBTOOL_EXECUTABLE} != "yes"
PKG_FAIL_REASON+= "EMBERBSD_DARWIN_LIBTOOL must select an executable file"
.else
CMAKE_CONFIGURE_ARGS.Darwin+= -DCMAKE_LIBTOOL:FILEPATH=${EMBERBSD_DARWIN_LIBTOOL:Q}
.endif
.endif
.endif
.endif
.endif
