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
.if ${USE_CROSS_COMPILE:tl} == "yes"
# cmd/dist writes CC_FOR_TARGET, CXX_FOR_TARGET and PKG_CONFIG into
# zdefaultcc.go as the installed toolchain's defaults. A cross-built
# toolchain does not run cgo for the target during the build, so record the
# command names on the target: the compiler without its directory, cross
# prefix and sysroot arguments.
_GO_BUILD_ENV+=	CC_FOR_TARGET=${CC:[1]:T:S/^${MACHINE_GNU_PLATFORM:U}-//:Q}
_GO_BUILD_ENV+=	CXX_FOR_TARGET=${CXX:[1]:T:S/^${MACHINE_GNU_PLATFORM:U}-//:Q}
.else
_GO_BUILD_ENV+=	CC_FOR_TARGET=${CC:Q} CXX_FOR_TARGET=${CXX:Q}
.endif
# Native and cross builds both record pkg-config by name: the work-directory
# tool wrapper that pkgsrc puts in the environment is gone after the build.
_GO_BUILD_ENV+=	PKG_CONFIG=pkg-config
_GO_BUILD_ENV+=	GOROOT_BOOTSTRAP=${GOROOT_BOOTSTRAP:Q}
_GO_BUILD_ENV+=	GOTOOLCHAIN=local GOENV=off
_GO_BUILD_ENV+=	GOMAXPROCS=${MAKE_JOBS:U1}
_GO_BUILD_ENV+=	GOCACHE=${WRKDIR}/.cache/go-build
