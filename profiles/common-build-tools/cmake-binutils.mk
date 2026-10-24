# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Retain selected tools and the wrapper transformations used by pkgsrc.
.if !defined(_EMBERBSD_CMAKE_BINUTILS_MK)
_EMBERBSD_CMAKE_BINUTILS_MK= yes
_EMBERBSD_CMAKE_BINUTILS_ARGS=
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
.for _cmake_var _pkgsrc_var in AR AR RANLIB RANLIB NM NM STRIP STRIP LINKER LD
.if empty(PKG_${_pkgsrc_var}:M/*) || !exists(${PKG_${_pkgsrc_var}})
PKG_FAIL_REASON+= "CMake requires ${_pkgsrc_var} to select an existing absolute executable"
.else
_EMBERBSD_CMAKE_BINUTIL_EXECUTABLE!= if test -f ${PKG_${_pkgsrc_var}:Q} && \
    test -x ${PKG_${_pkgsrc_var}:Q}; then echo yes; else echo no; fi
.if ${_EMBERBSD_CMAKE_BINUTIL_EXECUTABLE} != "yes"
PKG_FAIL_REASON+= "CMake requires ${_pkgsrc_var} to select an executable file"
.else
# Generated wrappers do not exist during metadata evaluation.
# Keep their work-directory expansion deferred until the full recipe is read.
.if ${_USE_CWRAPPERS} == "yes" && ${_pkgsrc_var} == "LD"
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DCMAKE_${_cmake_var}:FILEPATH=${WRAPPER_BINDIR:Q}/ld
.elif ${_USE_CWRAPPERS} == "no" && (${_pkgsrc_var} == "AR" || ${_pkgsrc_var} == "RANLIB" || ${_pkgsrc_var} == "LD")
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DCMAKE_${_cmake_var}:FILEPATH=${WRAPPER_BINDIR:Q}/${_pkgsrc_var:tl}
.else
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DCMAKE_${_cmake_var}:FILEPATH=${PKG_${_pkgsrc_var}:Q}
.endif
.endif
.endif
.endfor
.endif
.endif
