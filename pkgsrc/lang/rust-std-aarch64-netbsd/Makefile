# Origin: EmberBSD (AI-assisted); same-compiler target std, no rustc/LLVM rebuild.
DISTNAME= rustc-1.99.1-src
PKGNAME= rust-std-aarch64-netbsd-1.99.1
PKGREVISION= 3
CATEGORIES= lang
MASTER_SITES= https://static.rust-lang.org/dist/
EXTRACT_SUFX= .tar.xz

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://www.rust-lang.org/
COMMENT= NetBSD/AArch64 standard library for the shared macOS Rust compiler
LICENSE= mit OR apache-2.0

ONLY_FOR_PLATFORM= Darwin-*-aarch64 Darwin-*-x86_64
USE_LANGUAGES= c c++ # native bootstrap linker and compiler detection
PATCH_STRIP= -p1
DEPENDS+= rust-bin-1.99.1{,nb[0-9]*}:../../lang/rust-bin
PYTHON_FOR_BUILD_ONLY= tool

# These are foreign target data, not host-loadable Mach-O libraries.
# The mandatory check below verifies the target ELF and its actual providers.
CHECK_SHLIBS_SUPPORTED= no
CHECK_WRKREF+= work

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno} == "yes"
PKG_FAIL_REASON+= "Build this target-data package with the native host MAKECONF."
.endif
# GCC remains an explicit alternative with a documented platform reason.
EMBERBSD_RUST_TARGET_COMPILER_FAMILY?= clang
BUILD_DEFS+= EMBERBSD_RUST_TARGET_COMPILER_FAMILY EMBERBSD_RUST_GCC_REASON
.if ${EMBERBSD_RUST_TARGET_COMPILER_FAMILY} == "clang"
NO_CONFIGURE= yes
RUST_STD_TARGET= aarch64
.include "../../lang/rust-bin/files/target-std/llvm-producer.mk"
.elif ${EMBERBSD_RUST_TARGET_COMPILER_FAMILY} == "gcc"
.if empty(EMBERBSD_RUST_GCC_REASON:U)
PKG_FAIL_REASON+= "Explicit GCC alternative requires EMBERBSD_RUST_GCC_REASON."
.endif
.if ${MACHINE_ARCH} != "aarch64"
PKG_FAIL_REASON+= "The GCC producer supports Darwin/aarch64 hosts only."
.endif
HAS_CONFIGURE= yes
CONFIGURE_DIRS= .
.for var in EMBERBSD_RUST_CROSS_TOOLS EMBERBSD_RUST_TARGET_SYSROOT
.if empty(${var}:U)
PKG_FAIL_REASON+= "Set ${var} to the existing verified cross provider."
.endif
.endfor
BUILD_DEFS+= EMBERBSD_RUST_CROSS_TOOLS EMBERBSD_RUST_TARGET_SYSROOT
BUILD_DEFS+= EMBERBSD_RUST_BUILD_JOBS
EMBERBSD_RUST_BUILD_JOBS?= ${MAKE_JOBS:U1}

STD_SUBDIR= lib/rustlib/aarch64-unknown-netbsd
STD_OUTPUT= ${WRKDIR}/out/aarch64-apple-darwin/stage0-sysroot/${STD_SUBDIR}
STD_DESTINATION= ${DESTDIR}${PREFIX}/${STD_SUBDIR}
STD_HELPER= ${SETENV} EMBERBSD_RUST_BUILD_JOBS=${EMBERBSD_RUST_BUILD_JOBS:Q} \
    ${SH} ${FILESDIR}/target-std.sh
STD_ARGS= ${WRKSRC:Q} ${WRKDIR:Q} ${PREFIX:Q} \
    ${EMBERBSD_RUST_CROSS_TOOLS:Q} ${EMBERBSD_RUST_TARGET_SYSROOT:Q}
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX} && \
    find ${STD_SUBDIR} -type f -print | ${SORT};
INSTALLATION_DIRS= ${STD_SUBDIR} share/licenses/${PKGBASE}

# Reject overlapping build/provider paths before extracting the source archive.
pre-extract:
	${STD_HELPER} preflight ${WRKDIR:Q} ${WRKDIR:Q} ${PREFIX:Q} \
	    ${EMBERBSD_RUST_CROSS_TOOLS:Q} ${EMBERBSD_RUST_TARGET_SYSROOT:Q}

# x.py is Rust's existing upstream Python bootstrap, not a project helper.
do-configure:
	${STD_HELPER} configure ${STD_ARGS}

do-build:
	${STD_HELPER} build ${STD_ARGS} ${TOOL_PYTHONBIN:Q}

do-install:
	${CP} -R ${STD_OUTPUT:Q}/lib ${STD_DESTINATION:Q}
	${INSTALL_DATA} ${WRKSRC}/LICENSE-APACHE ${WRKSRC}/LICENSE-MIT ${WRKSRC}/COPYRIGHT \
	    ${DESTDIR}${PREFIX}/share/licenses/${PKGBASE}
	${STD_HELPER} check ${STD_ARGS} ${DESTDIR}${PREFIX}/${STD_SUBDIR}/lib

.else
PKG_FAIL_REASON+= "Unsupported Rust target compiler family."
.endif

.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
