# Origin: EmberBSD (AI-assisted). Sources use the canonical Clang pkgsrc recipe.
.include "../../lang/llvm/version.mk"
PKGNAME= clang-python-bindings-${LLVM_VERSION}
CATEGORIES= lang devel
HOMEPAGE= https://clang.llvm.org/
COMMENT= Python bindings for the shared Clang library
LICENSE= apache-2.0
NO_ARCH= yes
NO_CONFIGURE= yes
EXTRACT_ONLY=
WRKSRC= ${WRKDIR}
DISTINFO_FILE= ${.CURDIR}/../../lang/llvm/distinfo
USE_LANGUAGES= # Python sources
USE_TOOLS+= find sort
TOOL_DEPENDS+= patch-[0-9]*:../../devel/patch
DEPENDS+= clang-${LLVM_VERSION}{,nb*}:../../lang/clang
.include "../../mk/bsd.fast.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION= 1
DEPENDS+= clang>=23.1.4nb12:../../lang/clang
.endif
_CLANG_OWNER= ${_PKGSRCDIR}/lang/clang
_CLANG_OWNER_OBJ= ${WRKDIR}/clang-owner
_BINDINGS_DEST= ${DESTDIR}${PREFIX}/share/clang-python-bindings

do-build:
	${MAKE} -C ${_CLANG_OWNER:Q} WRKOBJDIR=${_CLANG_OWNER_OBJ:Q} SKIP_DEPENDS=yes patch

do-install:
	${RUN} source=`${MAKE} -C ${_CLANG_OWNER:Q} WRKOBJDIR=${_CLANG_OWNER_OBJ:Q} -V '$${WRKSRC}'`; \
	    ${INSTALL_DATA_DIR} ${_BINDINGS_DEST:Q}; \
	    ${CP} -R "$${source}/bindings/python/clang" ${_BINDINGS_DEST:Q}/; \
	    ${INSTALL_DATA} "$${source}/LICENSE.TXT" ${_BINDINGS_DEST:Q}/LICENSE.TXT

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/clang-python-bindings \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"
