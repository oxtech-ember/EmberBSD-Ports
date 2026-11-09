# $NetBSD$
.include "../../devel/lexilla/Makefile.common"
PKGNAME=	lexilla-${LEXILLA_VERSION}
COMMENT=	Syntax lexers implementing the Scintilla ILexer5 interface

.include "options.mk"
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
LEXILLA_LIB=	liblexilla.dylib
LEXILLA_SONAME=	liblexilla.${LEXILLA_VERSION:C/\..*//}.dylib
LEXILLA_VERSIONED=	liblexilla.${LEXILLA_VERSION}.dylib
.else
LEXILLA_LIB=	liblexilla.so
LEXILLA_SONAME=	liblexilla.so.${LEXILLA_VERSION:C/\..*//}
LEXILLA_VERSIONED=	liblexilla.so.${LEXILLA_VERSION}
.endif
PLIST_SUBST+=	LEXILLA_LIB=${LEXILLA_LIB} LEXILLA_SONAME=${LEXILLA_SONAME}
PLIST_SUBST+=	LEXILLA_VERSIONED=${LEXILLA_VERSIONED}
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} lib/cmake/Lexilla -name "LexillaTargets-*.cmake" -type f -print | ${SORT};

post-extract:
	${CP} ${FILESDIR}/CMakeLists.txt ${FILESDIR}/*.in ${WRKSRC}/
	${CP} -R ${.CURDIR}/tests ${WRKSRC}/emberbsd-tests

.include "../../devel/scintilla-core/buildlink3.mk"
.include "../../mk/emberbsd-native-cxx-runtime.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
