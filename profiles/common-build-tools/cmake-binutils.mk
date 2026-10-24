# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Retain selected tools and the wrapper transformations used by pkgsrc.
.if !defined(_EMBERBSD_CMAKE_BINUTILS_MK)
_EMBERBSD_CMAKE_BINUTILS_MK= yes
_EMBERBSD_CMAKE_BINUTILS_ARGS=
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DEMBERBSD_CMAKE_NATIVE_TOOLS:BOOL=ON
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DCMAKE_POLICY_DEFAULT_CMP0137:STRING=NEW
_EMBERBSD_CMAKE_TOOL_PAIRS= AR PKG_AR RANLIB PKG_RANLIB NM PKG_NM STRIP PKG_STRIP LINKER PKG_LD
.if ${OPSYS} == "Darwin"
.if empty(OSX_SDK_PATH:M/*) || !exists(${OSX_SDK_PATH})
PKG_FAIL_REASON+= "CMake requires OSX_SDK_PATH to select an existing absolute SDK directory"
.else
_EMBERBSD_CMAKE_SYSROOT_DIRECTORY!= if test -d ${OSX_SDK_PATH:Q}; then echo yes; else echo no; fi
.if ${_EMBERBSD_CMAKE_SYSROOT_DIRECTORY} != "yes"
PKG_FAIL_REASON+= "CMake requires OSX_SDK_PATH to select an SDK directory"
.else
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DCMAKE_OSX_SYSROOT:PATH=${OSX_SDK_PATH:Q}
.endif
.endif
_EMBERBSD_CMAKE_TOOL_PAIRS+= INSTALL_NAME_TOOL EMBERBSD_DARWIN_INSTALL_NAME_TOOL TAPI EMBERBSD_DARWIN_TAPI
.if ${EMBERBSD_DARWIN_TAPI_KIND:U:[#]} != 1 || \
    (empty(EMBERBSD_DARWIN_TAPI_KIND:Mapple) && empty(EMBERBSD_DARWIN_TAPI_KIND:Mllvm-readtapi))
PKG_FAIL_REASON+= "CMake requires EMBERBSD_DARWIN_TAPI_KIND to be apple or llvm-readtapi"
.else
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DEMBERBSD_DARWIN_TAPI_KIND:STRING=${EMBERBSD_DARWIN_TAPI_KIND}
.endif
.endif
.for _cmake_var _tool_var in ${_EMBERBSD_CMAKE_TOOL_PAIRS}
.if empty(${_tool_var}:M/*) || !exists(${${_tool_var}})
PKG_FAIL_REASON+= "CMake requires ${_tool_var} to select an existing absolute executable"
.else
_EMBERBSD_CMAKE_BINUTIL_EXECUTABLE!= if test -f ${${_tool_var}:Q} && \
    test -x ${${_tool_var}:Q}; then echo yes; else echo no; fi
.if ${_EMBERBSD_CMAKE_BINUTIL_EXECUTABLE} != "yes"
PKG_FAIL_REASON+= "CMake requires ${_tool_var} to select an executable file"
.else
# Generated wrappers do not exist during metadata evaluation.
# Keep their work-directory expansion deferred until the full recipe is read.
.if ${_USE_CWRAPPERS} == "yes" && ${_cmake_var} == "LINKER"
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DCMAKE_${_cmake_var}:FILEPATH=${WRAPPER_BINDIR:Q}/ld
.elif ${_USE_CWRAPPERS} == "no" && (${_cmake_var} == "AR" || ${_cmake_var} == "RANLIB" || ${_cmake_var} == "LINKER")
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DCMAKE_${_cmake_var}:FILEPATH=${WRAPPER_BINDIR:Q}/${_cmake_var:S/LINKER/LD/:tl}
.else
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DCMAKE_${_cmake_var}:FILEPATH=${${_tool_var}:Q}
.endif
.endif
.endif
.endfor
.endif
.endif
