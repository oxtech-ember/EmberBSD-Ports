# Origin: EmberBSD (AI-assisted); shared Rust source and selected LLVM runtime.
DISTNAME= rustc-1.99.1-src
PKGNAME= rust-std-wasm32-wasip1-1.99.1
CATEGORIES= lang
MASTER_SITES= https://static.rust-lang.org/dist/
EXTRACT_SUFX= .tar.xz
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://www.rust-lang.org/
COMMENT= WASI preview1 standard library for the shared Rust compiler
LICENSE= mit OR apache-2.0
ONLY_FOR_PLATFORM= Darwin-*-aarch64 Darwin-*-x86_64
USE_LANGUAGES= c c++
PATCH_STRIP= -p1
DEPENDS+= rust-bin-1.99.1{,nb[0-9]*}:../../lang/rust-bin
TOOL_DEPENDS+= wasi-libc-*:../../lang/wasi-libc
TOOL_DEPENDS+= wasi-compiler-rt-*:../../lang/wasi-compiler-rt
PYTHON_FOR_BUILD_ONLY= tool
CHECK_SHLIBS_SUPPORTED= no
CHECK_WRKREF+= work
NO_CONFIGURE= yes

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno} == "yes"
PKG_FAIL_REASON+= "Build this target-data package with the native host MAKECONF."
.endif
EMBERBSD_RUST_TARGET_COMPILER_FAMILY?= clang
BUILD_DEFS+= EMBERBSD_RUST_TARGET_COMPILER_FAMILY
.if ${EMBERBSD_RUST_TARGET_COMPILER_FAMILY} != "clang"
PKG_FAIL_REASON+= "The WASI Rust std producer currently supports Clang only."
.endif
RUST_STD_TARGET= wasm32-wasip1
.include "../../lang/rust-bin/files/target-std/llvm-producer.mk"

.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
