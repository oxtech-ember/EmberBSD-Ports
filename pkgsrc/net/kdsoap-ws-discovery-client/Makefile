# $NetBSD: Makefile,v 1.6 2026/09/02 19:03:57 wiz Exp $

DISTNAME=	kdsoap-ws-discovery-client-0.4.0
PKGREVISION=	5
CATEGORIES=	net kde
MASTER_SITES=	${MASTER_SITE_KDE:=kdsoap-ws-discovery-client/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://caspermeijn.gitlab.io/kdsoap-ws-discovery-client/
COMMENT=	WS-Discovery client library based on KDSoap
LICENSE=	cc0-1.0-universal AND gnu-gpl-v3

USE_LANGUAGES=		c c++

CMAKE_CONFIGURE_ARGS+=	-DQT_MAJOR_VERSION=6
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_Doxygen=ON

BUILDLINK_TRANSFORM+=	rm:-Wl,--fatal-warnings

.include "../../devel/cmake/build.mk"

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../devel/qt6-qttools/buildlink3.mk"
.include "../../net/kdsoap/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"

# Cross builds generate the WSDL code with the native kdwsdl2cpp from
# net/kdsoap-kdwsdl2cpp (same KDSoap release), through the upstream override
# knob.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
TOOL_DEPENDS+=	kdsoap-kdwsdl2cpp-2.2.0{,nb[0-9]*}:../../net/kdsoap-kdwsdl2cpp
CMAKE_CONFIGURE_ARGS+=	-DKDSOAP_KDWSDL2CPP_COMPILER=${TOOLBASE}/bin/kdwsdl2cpp-qt6
.endif
.include "../../mk/bsd.pkg.mk"
