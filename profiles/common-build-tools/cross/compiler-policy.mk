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
    !empty(USE_LANGUAGES:Mc++) && \
    empty(PKGPATH:Mlang/compiler-rt) && empty(PKGPATH:Mlang/llvm) && \
    empty(PKGPATH:Mlang/llvm-devel) && empty(PKGPATH:Mlang/clang) && \
    empty(PKGPATH:Mlang/libcxx*) && empty(PKGPATH:Mlang/libunwind*)
.include "${PKGSRCDIR}/lang/compiler-rt/application-runtime.mk"
.endif
