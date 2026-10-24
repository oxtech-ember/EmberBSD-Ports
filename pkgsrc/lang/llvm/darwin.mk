# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# The SDK producer supplies its qualified tool or an explicit scoped seed.
.if !defined(EMBERBSD_LLVM_DARWIN_MK)
EMBERBSD_LLVM_DARWIN_MK= yes
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes"
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
