# Origin: EmberBSD (AI-assisted); common upstream Undici provider.
DISTNAME= undici-8.12.3
PKGREVISION= 1
CATEGORIES= www
MASTER_SITES= -https://github.com/nodejs/undici/archive/refs/tags/v${PKGVERSION_NOREV}.tar.gz
HOMEPAGE= https://undici.nodejs.org/
COMMENT= Common Undici HTTP client and Node shared builtin
LICENSE= mit
NO_ARCH= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # JavaScript package
USE_TOOLS+= find sort
PYTHON_FOR_BUILD_ONLY= tool
TOOL_DEPENDS+= llhttp-wasi>=9.4.3:../../www/llhttp-wasi
.include "../../mk/bsd.prefs.mk"
EMBERBSD_UNDICI_HOST_PREFIX?= ${TOOLBASE}
.if empty(USE_CROSS_COMPILE:M[yY][eE][sS])
EMBERBSD_UNDICI_RUNTIME_PREFIX?= ${PREFIX}
.endif
BUILD_DEFS+= EMBERBSD_UNDICI_HOST_PREFIX EMBERBSD_UNDICI_RUNTIME_PREFIX
_UNDICI_DIR= ${PREFIX}/lib/node_modules/undici

do-build:
	${RUN} case x${EMBERBSD_UNDICI_HOST_PREFIX:Q} in x/*) ;; *) ${FAIL_MSG} "Select absolute EMBERBSD_UNDICI_HOST_PREFIX" ;; esac
	${RUN} case x${EMBERBSD_UNDICI_RUNTIME_PREFIX:Q} in x/*) ;; *) ${FAIL_MSG} "Select absolute EMBERBSD_UNDICI_RUNTIME_PREFIX" ;; esac
	${TOOL_PYTHONBIN:Q} -B -I -S ${FILESDIR:Q}/generate-wasm.py \
	    --wasm-dir ${EMBERBSD_UNDICI_HOST_PREFIX:Q}/share/llhttp-wasi \
	    --output-dir ${WRKSRC:Q}/lib/llhttp --loader ${WRKSRC:Q}/loader.js \
	    --install-dir ${EMBERBSD_UNDICI_RUNTIME_PREFIX:Q}/lib/node_modules/undici
	${RM} ${WRKSRC:Q}/lib/llhttp/llhttp.wasm ${WRKSRC:Q}/lib/llhttp/llhttp_simd.wasm

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${_UNDICI_DIR:Q}
	${CP} -R ${WRKSRC:Q}/lib ${WRKSRC:Q}/types ${DESTDIR:Q}${_UNDICI_DIR:Q}/
	${INSTALL_DATA} ${WRKSRC:Q}/index.js ${WRKSRC:Q}/index-fetch.js ${WRKSRC:Q}/index.d.ts \
	    ${WRKSRC:Q}/loader.js ${WRKSRC:Q}/package.json ${WRKSRC:Q}/LICENSE ${DESTDIR:Q}${_UNDICI_DIR:Q}/

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} lib/node_modules/undici \( -type f -o -type l \) -print | ${SORT};
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
