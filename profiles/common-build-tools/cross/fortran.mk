# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; late GCC16 Fortran policy after final option selection.
# GCC's Fortran runtime and intrinsic modules are a separate SDK role.
.if ${TOOLS_USE_CROSS_COMPILE:Uno:tl} == "yes" && \
    (!empty(USE_LANGUAGES:Mfortran) || !empty(USE_LANGUAGES:Mfortran77))
FC=${TOOLDIR}/bin/${_EMBER_CROSS_TRIPLET}-gfortran
.if !exists(${FC})
PKG_FAIL_REASON+="The selected GCC16 compiler generation has no Fortran frontend"
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
DEPENDS+=gcc16-fortran-runtime-16.2.0:../../lang/gcc16-fortran-runtime
BUILD_DEPENDS+=gcc16-fortran-devel-16.2.0:../../lang/gcc16-fortran-devel
.endif
# Fake-cross Libtool is a native host script. Its target runtime dependencies
# are checked in the SDK, never registered in the native package database.
EMBERBSD_FORTRAN_CAPABILITY?=
EMBERBSD_FORTRAN_PYTHON?=
EMBERBSD_FORTRAN_PORTS_SOURCE?=
.if empty(EMBERBSD_FORTRAN_CAPABILITY:M/*) || empty(EMBERBSD_FORTRAN_PYTHON:M/*) || empty(EMBERBSD_SDK_SOURCE:M/*) || empty(EMBERBSD_FORTRAN_PORTS_SOURCE:M/*)
PKG_FAIL_REASON+="Set absolute Fortran capability, host Python, Ports and explicit SDK source paths"
.else
_EMBER_FORTRAN_CHECK!=${EMBERBSD_FORTRAN_PYTHON:Q} -B ${EMBERBSD_FORTRAN_PORTS_SOURCE:Q}/profiles/development-toolchain/cross/check-fortran.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} --target ${EMBERBSD_CROSS_TARGET:Q} --compiler ${FC:Q} --capability ${EMBERBSD_FORTRAN_CAPABILITY:Q}
.if ${_EMBER_FORTRAN_CHECK:U} != "verified-gcc16-fortran"
PKG_FAIL_REASON+="The selected Fortran frontend does not match its completed capability receipt"
.endif
.endif
_EMBER_FORTRAN_SUPPORT=${CROSS_DESTDIR}/usr/pkg/gcc16/lib/gcc/${_EMBER_CROSS_TRIPLET}/16.2.0
.if !exists(${CROSS_DESTDIR}/usr/pkg/gcc16/lib/libgfortran.spec) || \
    !exists(${CROSS_DESTDIR}/usr/pkg/gcc16/lib/libgfortran.so) || \
    !exists(${CROSS_DESTDIR}/usr/pkg/gcc16/lib/libquadmath.so) || \
    !exists(${_EMBER_FORTRAN_SUPPORT}/include/ISO_Fortran_binding.h)
PKG_FAIL_REASON+="Install the verified GCC16 Fortran runtime and SDK roles before cross compilation"
.endif
CWRAPPERS_APPEND.f77+=-B${_EMBER_FORTRAN_SUPPORT}/
CWRAPPERS_APPEND.f77+=-B${CROSS_DESTDIR}/usr/pkg/gcc16/lib/
CWRAPPERS_APPEND.f77+=-fintrinsic-modules-path=${_EMBER_FORTRAN_SUPPORT}/finclude
CWRAPPERS_APPEND.f77+=-Wl,-rpath-link,${CROSS_DESTDIR}/usr/lib
.endif
