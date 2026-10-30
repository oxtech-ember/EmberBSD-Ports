# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native KWin Wayland protocol code generator
# for cross builds of x11/plasma6-kwin.

PKGNAME=	plasma6-kwin-qtwaylandscanner-${PLASMAVER}

.include "../../x11/plasma6-kwin/Makefile.common"

COMMENT=	Native KWin Wayland protocol code generator for cross builds

.include "../../meta-pkgs/kde/plasma6.mk"

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

# Upstream's standalone generator project needs only Qt Core and ECM.
CONFIGURE_DIR=	src/wayland/tools
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF

INSTALLATION_DIRS=	bin

do-install:
	${INSTALL_PROGRAM} \
	    ${WRKSRC}/${CONFIGURE_DIR}/${CMAKE_BUILD_DIR}/qtwaylandscanner_kde \
	    ${DESTDIR}${PREFIX}/bin/qtwaylandscanner_kde

.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
