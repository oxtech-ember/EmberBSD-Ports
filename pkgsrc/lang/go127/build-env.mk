# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted explicit Go build environment.
# Keep native bootstrap tools and target cgo commands separate.
.if ${USE_CROSS_COMPILE:tl} == "yes"
_GO_HOST_CC=	${NATIVE_CC}
_GO_HOST_CXX=	${NATIVE_CXX}
.else
_GO_HOST_CC=	${CC}
_GO_HOST_CXX=	${CXX}
.endif

_GO_BUILD_ENV=	${GOOPT}
_GO_BUILD_ENV+=	CC=${_GO_HOST_CC:Q} CXX=${_GO_HOST_CXX:Q}
_GO_BUILD_ENV+=	CC_FOR_TARGET=${CC:Q} CXX_FOR_TARGET=${CXX:Q}
_GO_BUILD_ENV+=	GOROOT_BOOTSTRAP=${GOROOT_BOOTSTRAP:Q}
_GO_BUILD_ENV+=	GOTOOLCHAIN=local GOENV=off
_GO_BUILD_ENV+=	GOMAXPROCS=${MAKE_JOBS:U1}
_GO_BUILD_ENV+=	GOCACHE=${WRKDIR}/.cache/go-build
