# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native Sonnet trigram generator for cross
# builds of textproc/kf6-sonnet.

.include "../../textproc/kf6-sonnet/Makefile.common"

PKGNAME=	kf6-sonnet-parsetrigrams-${KF6VER}
COMMENT=	Native Sonnet trigram generator for cross builds

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

# Upstream's build-host configuration: Sonnet Core without widgets, QML or
# spelling backends. Only the generator is built and installed.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DSONNET_USE_WIDGETS=OFF
CMAKE_CONFIGURE_ARGS+=	-DSONNET_USE_QML=OFF
CMAKE_CONFIGURE_ARGS+=	-DSONNET_NO_BACKENDS=ON
BUILD_TARGET=		parsetrigrams

# Both install bin/parsetrigrams6.
CONFLICTS+=	kf6-sonnet-[0-9]*

INSTALLATION_DIRS=	bin

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/${CMAKE_BUILD_DIR}/bin/parsetrigrams6 \
	    ${DESTDIR}${PREFIX}/bin/parsetrigrams6

.include "../../devel/qt6-qttools/linguist.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
