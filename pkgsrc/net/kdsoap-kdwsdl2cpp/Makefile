# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native KDSoap WSDL code generator for cross
# builds of KDSoap consumers.

.include "../../net/kdsoap/Makefile.common"

PKGNAME=	${DISTNAME:S/^kdsoap-/kdsoap-kdwsdl2cpp-/}
COMMENT=	Native KDSoap WSDL code generator for cross builds

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

# The build-host Qt has no QtNetwork: build only the generator
# (patch-CMakeLists.txt and the kdwsdl2cpp patches).
CMAKE_CONFIGURE_ARGS+=	-DKDSoap_CODEGENERATOR_ONLY=ON
CMAKE_CONFIGURE_ARGS+=	-DKDSoap_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+=	-DKDSoap_TESTS=OFF
BUILD_TARGET=		kdwsdl2cpp

# Both install bin/kdwsdl2cpp-qt6.
CONFLICTS+=	kdsoap-[0-9]*

INSTALLATION_DIRS=	bin

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/${CMAKE_BUILD_DIR}/bin/kdwsdl2cpp-qt6 \
	    ${DESTDIR}${PREFIX}/bin/kdwsdl2cpp-qt6

.include "../../devel/cmake/build.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
