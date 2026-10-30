# Origin: EmberBSD (AI-assisted); selected common LLVM and wasi-libc source.
.include "../../lang/llvm/version.mk"
DISTNAME= wasi-libc-0.0.0pre20260819
EXTRACT_SUFX= .tar.gz
EXTRACT_ELEMENTS=
CATEGORIES= lang
MASTER_SITES= ${MASTER_SITE_GITHUB:=WebAssembly/}
GITHUB_PROJECT= wasi-libc
GITHUB_TYPE= tag
GITHUB_TAG= 2e6fb9d8ee0cdf9e431fbcabe8af3115de000a13
GITHUB_SUBMODULES+= WebAssembly WASI 59cbe140561db52fc505555e859de884e0ee7f00 tools/wasi-headers/WASI
WRKSRC= ${WRKDIR}/wasi-libc-${GITHUB_TAG}
EXTRACT_USING= bsdtar
HOMEPAGE= https://github.com/WebAssembly/wasi-libc/
COMMENT= C library for WebAssembly WASI preview1
LICENSE= mit AND apache-2.0
USE_LANGUAGES= c
USE_TOOLS+= find sed sort
# The unused upstream POSIX test-suite scripts use "==" in test(1).
CHECK_PORTABILITY_SKIP+= test/open-posix-test-suite/*
SSP_SUPPORTED= no
PKGSRC_USE_STACK_CHECK= no
RELRO_SUPPORTED= no
TOOL_DEPENDS+= wasi-compiler-rt-${LLVM_VERSION}*:../../lang/wasi-compiler-rt
TOOL_DEPENDS+= cmake-[0-9]*:../../devel/cmake
TOOL_DEPENDS+= ninja-build-[0-9]*:../../devel/ninja-build
TOOL_DEPENDS+= clang-${LLVM_VERSION}*:../../lang/clang
TOOL_DEPENDS+= llvm-${LLVM_VERSION}*:../../lang/llvm
TOOL_DEPENDS+= lld-${LLVM_VERSION}*:../../devel/lld

EMBERBSD_WASI_HOST_PREFIX?= ${TOOLBASE}
BUILD_DEFS+= EMBERBSD_WASI_HOST_PREFIX
.if empty(EMBERBSD_WASI_HOST_PREFIX:M/*)
PKG_FAIL_REASON+= "Select EMBERBSD_WASI_HOST_PREFIX as an absolute path."
.endif
WASI_BUILTINS_LIB?= ${EMBERBSD_WASI_HOST_PREFIX}/lib/clang/${LLVM_MAJOR_VERSION}/lib/wasm32-unknown-wasip1/libclang_rt.builtins.a
_WASI_BUILD= ${WRKDIR}/wasi-build

do-configure:
	${TEST} -f ${WASI_BUILTINS_LIB:Q}
	${MKDIR} ${WRKDIR:Q}/wasi-empty-sysroot
	${SETENV} ${CONFIGURE_ENV} ${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/cmake -S ${WRKSRC:Q} -B ${_WASI_BUILD:Q} -G Ninja \
	    -DCMAKE_MAKE_PROGRAM=${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/ninja -DTARGET_TRIPLE=wasm32-wasip1 \
	    -DBINDINGS_TARGET=OFF -DUSE_WASM_COMPONENT_LD=OFF -DBUILTINS_LIB=${WASI_BUILTINS_LIB:Q} \
	    -DCMAKE_INSTALL_PREFIX=${PREFIX:Q}/wasi -DCMAKE_SYSROOT=${WRKDIR:Q}/wasi-empty-sysroot \
	    -DCMAKE_C_FLAGS:STRING= -DCMAKE_ASM_FLAGS:STRING= -DCMAKE_ASM_COMPILER_TARGET=wasm32-wasip1 \
	    -DCMAKE_C_COMPILER=${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/clang -DCMAKE_ASM_COMPILER=${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/clang \
	    -DCMAKE_AR=${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/llvm-ar -DCMAKE_RANLIB=${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/llvm-ranlib \
	    -DCMAKE_NM=${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/llvm-nm -DCMAKE_LINKER=${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/wasm-ld \
	    -DSED=${SED:Q} -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY -DCMAKE_BUILD_TYPE=Release

do-build:
	${SETENV} ${MAKE_ENV} ${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/cmake --build ${_WASI_BUILD:Q} --parallel ${MAKE_JOBS:U1} --target sysroot

do-install:
	${SETENV} ${INSTALL_ENV} DESTDIR=${DESTDIR:Q} ${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/cmake --install ${_WASI_BUILD:Q}

post-install:
	${LN} -s wasm32-wasip1 ${DESTDIR:Q}${PREFIX:Q}/wasi/include/wasm32-wasi
	${LN} -s wasm32-wasip1 ${DESTDIR:Q}${PREFIX:Q}/wasi/lib/wasm32-wasi
	${MKDIR} ${DESTDIR:Q}${PREFIX:Q}/share/licenses/wasi-libc
	${INSTALL_DATA} ${WRKSRC:Q}/LICENSE* ${DESTDIR:Q}${PREFIX:Q}/share/licenses/wasi-libc/

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} wasi share/licenses/wasi-libc \( -type f -o -type l \) -print | ${SORT};

.include "../../mk/bsd.pkg.mk"
