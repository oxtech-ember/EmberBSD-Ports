# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native syntax definition indexer for cross
# builds of textproc/kf6-syntax-highlighting.

.include "../../textproc/kf6-syntax-highlighting/Makefile.common"

PKGNAME=	kf6-syntax-highlighting-indexer-${KF6VER}
COMMENT=	Native syntax definition indexer for cross builds

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

# Upstream's build-host configuration (src/indexer builds it the same way
# for its own cross fallback): no QtGui components, so QtCore suffices
# (patch-CMakeLists.txt). Only the indexer is built; it validates the
# definitions with Xerces-C as in a native build.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DKSYNTAXHIGHLIGHTING_USE_GUI=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_Python=ON
BUILD_TARGET=		katehighlightingindexer

USE_TOOLS+=	perl

INSTALLATION_DIRS=	bin

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/${CMAKE_BUILD_DIR}/bin/katehighlightingindexer \
	    ${DESTDIR}${PREFIX}/bin/katehighlightingindexer

.include "../../devel/qt6-qttools/linguist.mk"
.include "../../textproc/xerces-c/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"
