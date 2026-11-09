# $NetBSD$
.include "../../devel/scintilla-core/Makefile.common"
PKGNAME=	scintilla-core-${SCINTILLA_VERSION}
COMMENT=	Toolkit-free PIC editing core for Scintilla frontends

.include "options.mk"
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} lib/cmake/ScintillaCore -name "ScintillaCoreTargets-*.cmake" -type f -print | ${SORT};

post-extract:
	${CP} ${FILESDIR}/CMakeLists.txt ${FILESDIR}/*.in ${WRKSRC}/
	${CP} -R ${.CURDIR}/tests ${WRKSRC}/emberbsd-tests

.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/emberbsd-native-cxx-runtime.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
