# Origin: EmberBSD (AI-assisted).  Source and patches are owned by llhttp.
.include "../../www/llhttp/Makefile.common"
PKGNAME= llhttp-wasi-${LLHTTP_VERSION}
COMMENT= HTTP parser WebAssembly reactors for WASI preview1
NO_ARCH= yes
USE_LANGUAGES= c
DISTINFO_FILE= ${.CURDIR}/../../www/llhttp/distinfo
PATCHDIR= ${.CURDIR}/../../www/llhttp/patches
TOOL_DEPENDS+= clang-[0-9]*:../../lang/clang
TOOL_DEPENDS+= lld-[0-9]*:../../devel/lld
TOOL_DEPENDS+= wasi-compiler-rt-[0-9]*:../../lang/wasi-compiler-rt
TOOL_DEPENDS+= wasi-libc>=0.0.0pre20260819:../../lang/wasi-libc
.include "../../mk/bsd.prefs.mk"
EMBERBSD_WASI_HOST_PREFIX?= ${TOOLBASE}
BUILD_DEFS+= EMBERBSD_WASI_HOST_PREFIX
.if empty(EMBERBSD_WASI_HOST_PREFIX:M/*)
PKG_FAIL_REASON+= "Select EMBERBSD_WASI_HOST_PREFIX as an absolute path."
.endif
_WASI_CC= ${EMBERBSD_WASI_HOST_PREFIX}/bin/clang
_WASI_SYSROOT= ${EMBERBSD_WASI_HOST_PREFIX}/wasi
_WASI_FLAGS= --target=wasm32-wasip1 --sysroot=${_WASI_SYSROOT:Q} \
    -fuse-ld=${EMBERBSD_WASI_HOST_PREFIX:Q}/bin/wasm-ld \
    -O3 -fno-exceptions -fvisibility=hidden -mexec-model=reactor \
    -Wl,--allow-undefined-file=${FILESDIR:Q}/wasm-imports.txt \
    -Wl,--export-dynamic,--export-table,--export=malloc,--export=free,--no-entry
_WASI_SOURCES= ${WRKSRC:Q}/src/api.c ${WRKSRC:Q}/src/http.c ${WRKSRC:Q}/src/llhttp.c
NO_CONFIGURE= yes

do-build:
	${_WASI_CC:Q} ${_WASI_FLAGS} -I${WRKSRC:Q}/include ${_WASI_SOURCES} -o ${WRKDIR:Q}/llhttp.wasm
	${_WASI_CC:Q} ${_WASI_FLAGS} -msimd128 -I${WRKSRC:Q}/include ${_WASI_SOURCES} -o ${WRKDIR:Q}/llhttp_simd.wasm

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/llhttp-wasi
	${INSTALL_DATA} ${WRKDIR:Q}/llhttp.wasm ${WRKDIR:Q}/llhttp_simd.wasm ${DESTDIR:Q}${PREFIX:Q}/share/llhttp-wasi/
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/licenses/llhttp-wasi
	${INSTALL_DATA} ${WRKSRC:Q}/LICENSE-MIT ${DESTDIR:Q}${PREFIX:Q}/share/licenses/llhttp-wasi/

.include "../../mk/bsd.pkg.mk"
