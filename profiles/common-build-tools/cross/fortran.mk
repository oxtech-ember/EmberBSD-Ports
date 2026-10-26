# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; late language policy after final option selection.
# GCC's Fortran runtime and intrinsic modules are a separate SDK role.
.if ${TOOLS_USE_CROSS_COMPILE:Uno:tl} == "yes" && \
    ${EMBERBSD_CROSS_COMPILER_FAMILY:Uclang} == "clang" && \
    ${PKGSRC_COMPILER} != "clang"
.error The selected Clang cross profile does not permit a package compiler substitution
.endif
.if ${TOOLS_USE_CROSS_COMPILE:Uno:tl} == "yes" && \
    (!empty(USE_LANGUAGES:Mfortran) || !empty(USE_LANGUAGES:Mfortran77))
.if ${EMBERBSD_CROSS_COMPILER_FAMILY:Uclang} != "gcc"
PKG_FAIL_REASON+="Select the GCC cross profile and its common Fortran provider for Fortran packages"
.else
FC=${TOOLDIR}/bin/${_EMBER_CROSS_TRIPLET}-gfortran
.if !exists(${FC})
PKG_FAIL_REASON+="The selected GCC16 compiler generation has no Fortran frontend"
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
DEPENDS+=gcc16-fortran-runtime-16.2.0nb1:../../lang/gcc16-fortran-runtime
BUILD_DEPENDS+=gcc16-fortran-devel-16.2.0nb1:../../lang/gcc16-fortran-devel
.endif
# Fake-cross Libtool is a native host script. Its target runtime dependencies
# are checked in the SDK, never registered in the native package database.
EMBERBSD_FORTRAN_CAPABILITY?=
EMBERBSD_FORTRAN_PYTHON?=
EMBERBSD_FORTRAN_PORTS_SOURCE?=
.if empty(EMBERBSD_FORTRAN_CAPABILITY:M/*) || empty(EMBERBSD_FORTRAN_PYTHON:M/*) || empty(EMBERBSD_SDK_SOURCE:M/*) || empty(EMBERBSD_FORTRAN_PORTS_SOURCE:M/*)
PKG_FAIL_REASON+="Set absolute Fortran capability, host Python, Ports and explicit SDK source paths"
.else
_EMBER_FORTRAN_ALIASES!=${EMBERBSD_FORTRAN_PYTHON:Q} -I -S -B ${EMBERBSD_FORTRAN_PORTS_SOURCE:Q}/pkgsrc/lang/gcc16-fortran-runtime/files/fortran_target.py --target ${EMBERBSD_CROSS_TARGET:Q} || printf '\n%s\n' invalid-gcc16-fortran-target
.if empty(_EMBER_FORTRAN_ALIASES) || !empty(_EMBER_FORTRAN_ALIASES:Minvalid-gcc16-fortran-target)
PKG_FAIL_REASON+="Cannot obtain the GCC16 Fortran target library contract"
_EMBER_FORTRAN_ALIASES=
.endif
_EMBER_FORTRAN_CHECK!=${EMBERBSD_FORTRAN_PYTHON:Q} -B ${EMBERBSD_FORTRAN_PORTS_SOURCE:Q}/profiles/development-toolchain/cross/check-fortran.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} --target ${EMBERBSD_CROSS_TARGET:Q} --compiler ${FC:Q} --capability ${EMBERBSD_FORTRAN_CAPABILITY:Q}
.if ${_EMBER_FORTRAN_CHECK:U} != "verified-gcc16-fortran"
PKG_FAIL_REASON+="The selected Fortran frontend does not match its completed capability receipt"
.endif
.endif
_EMBER_FORTRAN_SUPPORT=${CROSS_DESTDIR}/usr/pkg/gcc16/lib/gcc/${_EMBER_CROSS_TRIPLET}/16.2.0
.if !exists(${CROSS_DESTDIR}/usr/pkg/gcc16/lib/libgfortran.spec) || \
    !exists(${_EMBER_FORTRAN_SUPPORT}/include/ISO_Fortran_binding.h)
PKG_FAIL_REASON+="Install the verified GCC16 Fortran runtime and SDK roles before cross compilation"
.endif
.for _alias in ${_EMBER_FORTRAN_ALIASES:U}
.if !exists(${CROSS_DESTDIR}/usr/pkg/gcc16/lib/${_alias})
PKG_FAIL_REASON+="Install the verified GCC16 Fortran runtime and SDK roles before cross compilation"
.endif
.endfor
CWRAPPERS_APPEND.f77+=-B${_EMBER_FORTRAN_SUPPORT}/
CWRAPPERS_APPEND.f77+=-B${CROSS_DESTDIR}/usr/pkg/gcc16/lib/
CWRAPPERS_APPEND.f77+=-fintrinsic-modules-path=${_EMBER_FORTRAN_SUPPORT}/finclude
CWRAPPERS_APPEND.f77+=-Wl,-rpath-link,${CROSS_DESTDIR}/usr/lib
.endif
.endif
