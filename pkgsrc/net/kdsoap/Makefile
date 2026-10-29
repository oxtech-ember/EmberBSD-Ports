# $NetBSD: Makefile,v 1.27 2026/09/02 19:03:57 wiz Exp $

PKGREVISION=	5

.include "Makefile.common"

COMMENT=	Qt-based client-side and server-side SOAP component

.include "../../devel/cmake/build.mk"

.include "../../x11/qt6-qtbase/buildlink3.mk"

# Examples execute the target-built kdwsdl2cpp tool on the host; the
# library and the tool itself build fine without them.
CMAKE_CONFIGURE_ARGS+=	-DKDSoap_EXAMPLES=OFF
.include "../../mk/bsd.pkg.mk"
