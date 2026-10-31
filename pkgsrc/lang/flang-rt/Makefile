# $NetBSD$

.include "../../lang/llvm/version.mk"

PKGNAME=	flang-rt-${LLVM_VERSION}
PKGREVISION=	4
CATEGORIES=	lang devel

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://flang.llvm.org/docs/
COMMENT=	Runtime library and intrinsic modules for LLVM Flang
LICENSE=	apache-2.0

# Flang-RT builds only through the LLVM runtimes build, which reads the LLVM
# CMake modules and the Flang headers.
WRKSRC=			${WRKDIR}/${DISTNAME}
CONFIGURE_DIR=		runtimes
EXTRACT_ELEMENTS+=	${DISTNAME}/llvm
EXTRACT_ELEMENTS+=	${DISTNAME}/flang

USE_CXX_FEATURES+=	c++17
# Fortran is built by the Flang named below, not by the pkgsrc Fortran
# provider: the runtime and intrinsic modules must match that Flang.
USE_LANGUAGES=		c c++

# The build-host Flang selected by the host toolset include, as for every
# Fortran package.
.if empty(EMBERBSD_FLANG:U:M/*) || !exists(${EMBERBSD_FLANG:U/nonexistent})
PKG_FAIL_REASON+=	"EMBERBSD_FLANG must select the build-host Ports flang driver"
.else
# The runtime and its modules belong to one Flang release.
.include "${PKGSRCDIR}/EMBERBSD-CROSS-FLANG-VERSION.MK"
.  if "${_EMBER_FLANG_MAJOR}" != "${LLVM_MAJOR_VERSION}"
PKG_FAIL_REASON+=	"EMBERBSD_FLANG is Flang ${_EMBER_FLANG_VERSION}, not LLVM ${LLVM_MAJOR_VERSION}"
.  endif
.endif

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DLLVM_ENABLE_RUNTIMES=flang-rt
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_Fortran_COMPILER=${EMBERBSD_FLANG}
# CMake's Fortran compiler check links a program, which needs the runtime
# this package builds; skip only that check, as the Flang-RT README says.
# C and C++ checks still link, so CMake finds the libraries the shared
# runtime needs (libm, libexecinfo).
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_Fortran_COMPILER_WORKS=yes
CMAKE_CONFIGURE_ARGS+=	-DLLVM_INCLUDE_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DFLANG_RT_INCLUDE_TESTS=OFF
# One shared runtime per process: Fortran libraries loaded together share
# I/O units and allocator state. The runtime is a normal library with a
# versioned name; no static copy is built.
CMAKE_CONFIGURE_ARGS+=	-DFLANG_RT_ENABLE_SHARED=ON
CMAKE_CONFIGURE_ARGS+=	-DFLANG_RT_ENABLE_STATIC=OFF
CMAKE_CONFIGURE_ARGS+=	-DFLANG_RT_INSTALL_SHARED_LIB_PATH:STRING=lib
CMAKE_CONFIGURE_ARGS+=	-DFLANG_RT_SHARED_SOVERSION=${LLVM_MAJOR_VERSION}
# The intrinsic modules install into the Flang resource directory, as
# compiler-rt does for Clang; the shared library above installs into lib.
# The path must be typed: an untyped relative value is made absolute against
# the configure directory.
CMAKE_CONFIGURE_ARGS+=	-DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=OFF
CMAKE_CONFIGURE_ARGS+=	-DRUNTIMES_INSTALL_RESOURCE_PATH:STRING=lib/clang/${LLVM_MAJOR_VERSION}
# Name the target explicitly so the library and module directories match
# the PLIST, and so a cross build compiles for the target.
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_Fortran_COMPILER_TARGET=${MACHINE_GNU_PLATFORM}
CMAKE_CONFIGURE_ARGS+=	-DLLVM_DEFAULT_TARGET_TRIPLE=${MACHINE_GNU_PLATFORM}
PLIST_SUBST+=		FLANG_RT_TRIPLE=${MACHINE_GNU_PLATFORM}
# The build uses only the modules it builds, not a configuration file that
# an installed copy of this package left beside the selected driver. CMake
# takes the initial Fortran flags from FFLAGS.
FFLAGS+=		--no-default-config

# The Darwin driver's default triple carries the full kernel version, such
# as aarch64-apple-darwin27.0.0, and Flang looks for intrinsic modules only
# under that exact name. Its configuration file lookup also tries the major
# version, which is the module directory above. A configuration file beside
# the driver names that directory, so plain flang finds the modules. An
# explicit --target or --no-default-config does not read it.
PLIST_VARS+=		drivercfg
.if ${OPSYS} == "Darwin"
PLIST.drivercfg=	yes
INSTALLATION_DIRS+=	bin
FLANG_RT_DRIVER_CFG=	bin/${MACHINE_GNU_PLATFORM}-flang.cfg

post-install:
	${PRINTF} '%s\n' \
	    '-fintrinsic-modules-path=<CFGDIR>/../lib/clang/${LLVM_MAJOR_VERSION}/finclude/flang/${MACHINE_GNU_PLATFORM}' \
	    > ${DESTDIR}${PREFIX}/${FLANG_RT_DRIVER_CFG}
.endif

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
