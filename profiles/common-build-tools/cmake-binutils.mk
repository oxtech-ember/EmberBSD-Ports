# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Retain selected tools and the wrapper transformations used by pkgsrc.
.if !defined(_EMBERBSD_CMAKE_BINUTILS_MK)
_EMBERBSD_CMAKE_BINUTILS_MK= yes
_EMBERBSD_CMAKE_BINUTILS_ARGS=
# Fetching and checking sources do not configure or execute CMake.  Keep
# validation for the default goal and for any mixture containing a build goal.
_EMBERBSD_CMAKE_BUILD_GOALS:= ${.TARGETS}
.for _source_goal in fetch checksum checksum-phase makesum makepatchsum distinfo \
    fetch-list fetch-list-one-package fetch-list-recursive mirror-distfiles \
    show-distfiles depends-fetch depends-checksum
_EMBERBSD_CMAKE_BUILD_GOALS:= ${_EMBERBSD_CMAKE_BUILD_GOALS:N${_source_goal}}
.endfor
.if empty(.TARGETS) || !empty(_EMBERBSD_CMAKE_BUILD_GOALS)
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DEMBERBSD_CMAKE_NATIVE_TOOLS:BOOL=ON
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DCMAKE_POLICY_DEFAULT_CMP0137:STRING=NEW
_EMBERBSD_CMAKE_TOOL_PAIRS= AR PKG_AR RANLIB PKG_RANLIB NM PKG_NM STRIP PKG_STRIP LINKER PKG_LD
.if ${OPSYS} == "Darwin"
_EMBERBSD_CMAKE_TOOL_PHASE= ${EMBERBSD_DARWIN_TOOL_PHASE:Ufull}
.if ${_EMBERBSD_CMAKE_TOOL_PHASE} != "full" && ${_EMBERBSD_CMAKE_TOOL_PHASE} != "initial"
PKG_FAIL_REASON+= "EMBERBSD_DARWIN_TOOL_PHASE must be initial or full"
.else
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DEMBERBSD_DARWIN_TOOL_PHASE:STRING=${_EMBERBSD_CMAKE_TOOL_PHASE}
.endif
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
.for _cmake_optional _optional_selector in INSTALL_NAME_TOOL EMBERBSD_DARWIN_INSTALL_NAME_TOOL TAPI EMBERBSD_DARWIN_TAPI
.if ${_EMBERBSD_CMAKE_TOOL_PHASE} != "initial" || !empty(${_optional_selector})
_EMBERBSD_CMAKE_TOOL_PAIRS+= ${_cmake_optional} ${_optional_selector}
.endif
.endfor
# Source-owned bootstrap inputs also cover CMake's own bootstrap cache.
.if ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} == "yes"
.if ${_EMBERBSD_CMAKE_TOOL_PHASE} != "initial"
_EMBERBSD_CMAKE_TOOL_PAIRS+= LIBTOOL EMBERBSD_DARWIN_LIBTOOL
.endif
.if defined(EMBERBSD_DARWIN_CMAKE_LINKER_LAUNCHER) && !empty(EMBERBSD_DARWIN_CMAKE_LINKER_LAUNCHER)
.for _ember_cmake_language in C CXX
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DCMAKE_${_ember_cmake_language}_LINKER_LAUNCHER:STRING=${EMBERBSD_DARWIN_CMAKE_LINKER_LAUNCHER:Q}
.endfor
.elif ${EMBERBSD_DARWIN_JOBS:U1} > 1
PKG_FAIL_REASON+= "Parallel CMake bootstrap requires the accepted SDK link launcher list"
.endif
.endif
.if ${_EMBERBSD_CMAKE_TOOL_PHASE} != "initial" || !empty(EMBERBSD_DARWIN_TAPI)
.if ${EMBERBSD_DARWIN_TAPI_KIND:U:[#]} != 1 || \
    (empty(EMBERBSD_DARWIN_TAPI_KIND:Mapple) && empty(EMBERBSD_DARWIN_TAPI_KIND:Mllvm-readtapi))
PKG_FAIL_REASON+= "CMake requires EMBERBSD_DARWIN_TAPI_KIND to be apple or llvm-readtapi"
.else
_EMBERBSD_CMAKE_BINUTILS_ARGS+= -DEMBERBSD_DARWIN_TAPI_KIND:STRING=${EMBERBSD_DARWIN_TAPI_KIND}
.endif
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
.else
# Cross target identity and rooted lookup from the common cross profile.
_EMBERBSD_CMAKE_BINUTILS_ARGS+= ${EMBERBSD_CROSS_CMAKE_ARGS}
.endif
.endif
.endif
