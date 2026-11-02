# SPDX-License-Identifier: BSD-2-Clause
# Late compiler policy, after options have selected the package languages.
.if exists(${.PARSEDIR}/fortran.mk)
.include "${.PARSEDIR}/fortran.mk"
.else
.include "${.PARSEDIR}/EMBERBSD-CROSS-FORTRAN.MK"
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && \
    ${TOOLS_USE_CROSS_COMPILE:Uno:tl} == "yes" && \
    ${EMBERBSD_CROSS_COMPILER_FAMILY:Uclang} == "clang" && \
    ${_EMBER_TARGET_RUNTIME_KIND:U} != "c-only" && \
    !empty(USE_LANGUAGES:M*++*) && \
    empty(PKGPATH:Mlang/compiler-rt) && empty(PKGPATH:Mlang/llvm) && \
    empty(PKGPATH:Mlang/llvm-devel) && empty(PKGPATH:Mlang/clang) && \
    empty(PKGPATH:Mlang/libcxx*) && empty(PKGPATH:Mlang/libunwind*)
.include "${PKGSRCDIR}/lang/compiler-rt/application-runtime.mk"
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && \
    ${TOOLS_USE_CROSS_COMPILE:Uno:tl} == "yes" && \
    ${EMBERBSD_CROSS_COMPILER_FAMILY:Uclang} == "clang" && \
    ${_EMBER_TARGET_RUNTIME_KIND:U} == "c-only" && \
    !empty(USE_LANGUAGES:Nc:Nc99:Ngnu99:Nc11:Ngnu11:Nc17:Ngnu17:Nasm)
PKG_FAIL_REASON+="Selected Clang target runtime supports only C and assembly"
.endif
