# QuickJS-ng API used by Telegram/widget-sandbox, kept distinct from Bellard QuickJS.
DISTNAME=       quickjs-ng-0.17.0
PKGNAME=        ${DISTNAME}
CATEGORIES=     lang
MASTER_SITES=   ${MASTER_SITE_GITHUB:=TelegramMessenger/}
GITHUB_PROJECT= quickjs
GITHUB_TAG=     fbc91d85432b967d5ad112308e6c752f7b5a9417
WRKSRC=         ${WRKDIR}/quickjs-${GITHUB_TAG}
DIST_SUBDIR=    quickjs-ng

HOMEPAGE=       https://github.com/TelegramMessenger/quickjs
COMMENT=        QuickJS-ng JavaScript engine shared library
LICENSE=        mit

USE_LANGUAGES=  c
USE_TOOLS+=     pkg-config

CMAKE_CONFIGURE_ARGS+=  -DBUILD_SHARED_LIBS:BOOL=ON
CMAKE_CONFIGURE_ARGS+=  -DQJS_ENABLE_INSTALL:BOOL=ON
CMAKE_CONFIGURE_ARGS+=  -DQJS_INSTALL_LIBRARY_ONLY:BOOL=ON
CMAKE_CONFIGURE_ARGS+=  -DCMAKE_INSTALL_INCLUDEDIR:PATH=include/quickjs-ng
CMAKE_CONFIGURE_ARGS+=  -DCMAKE_INSTALL_LIBDIR:PATH=lib
BUILD_TARGET=           qjs

SUBST_CLASSES+=         pkgconfig
SUBST_STAGE.pkgconfig=  pre-configure
SUBST_FILES.pkgconfig=  quickjs-ng.pc
SUBST_VARS.pkgconfig+=  PREFIX
SUBST_VARS.pkgconfig+=  COMPILER_RPATH_FLAG

INSTALLATION_DIRS+=     lib/pkgconfig share/licenses/${PKGBASE}


post-extract:
	${CP} ${FILESDIR}/quickjs-ng.pc ${WRKSRC}/quickjs-ng.pc

post-install:
	${INSTALL_DATA} ${WRKSRC}/quickjs-ng.pc \
	    ${DESTDIR}${PREFIX}/lib/pkgconfig/quickjs-ng.pc
	${INSTALL_DATA} ${WRKSRC}/LICENSE \
	    ${DESTDIR}${PREFIX}/share/licenses/${PKGBASE}/LICENSE

.include "../../devel/cmake/build.mk"

PLIST_VARS+=            darwin elf
.if ${OPSYS} == "Darwin"
PLIST.darwin=           yes
.else
PLIST.elf=              yes
.endif

.include "../../mk/bsd.pkg.mk"
