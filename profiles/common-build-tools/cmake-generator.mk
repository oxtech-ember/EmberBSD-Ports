# SPDX-License-Identifier: BSD-2-Clause
# Select a stable CMake generator for SDK builds without changing configured workdirs.

.if !empty(EMBERBSD_SDK_SOURCE) && !defined(CMAKE_GENERATOR)
_EMBER_CMAKE_WORK=	${WRKSRC}/${CONFIGURE_DIR:U.}/${CMAKE_BUILD_DIR:Ucmake-pkgsrc-build}
.  if exists(${_EMBER_CMAKE_WORK}/CMakeCache.txt)
.    if exists(${_EMBER_CMAKE_WORK}/Makefile) && !exists(${_EMBER_CMAKE_WORK}/build.ninja)
CMAKE_GENERATOR=	make
.    elif !exists(${_EMBER_CMAKE_WORK}/build.ninja) || exists(${_EMBER_CMAKE_WORK}/Makefile)
CMAKE_GENERATOR!=	${SED} -n -e 's/^CMAKE_GENERATOR:INTERNAL=Unix Makefiles$$/make/p' \
			    -e 's/^CMAKE_GENERATOR:INTERNAL=Ninja$$/ninja/p' ${_EMBER_CMAKE_WORK:Q}/CMakeCache.txt
.    endif
.  endif
.  if empty(CMAKE_GENERATOR)
CMAKE_GENERATOR=	ninja
.  endif
.endif
