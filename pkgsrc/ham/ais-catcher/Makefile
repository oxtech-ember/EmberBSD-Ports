# $NetBSD$

DISTNAME=	AIS-catcher-0.71
PKGNAME=	${DISTNAME:tl}
CATEGORIES=	ham
MASTER_SITES=	${MASTER_SITE_GITHUB:=jvde-github/}
GITHUB_PROJECT=	AIS-catcher
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/jvde-github/AIS-catcher
COMMENT=	Dual-channel AIS receiver with RTL-SDR and raw IQ input
LICENSE=	gnu-gpl-v3

USE_LANGUAGES=	c c++
USE_CXX_FEATURES=	c++11
USE_TOOLS+=	pkg-config
CMAKE_CONFIGURE_ARGS+=	-C ${FILESDIR}/receiver.cmake

INSTALLATION_DIRS+=	share/doc/ais-catcher
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/doc/ais-catcher/LICENSE

.include "../../devel/cmake/build.mk"
BUILDLINK_API_DEPENDS.rtl-sdr+=	rtl-sdr>=2.0.3
.include "../../ham/rtl-sdr/buildlink3.mk"
BUILDLINK_API_DEPENDS.libusb1+=	libusb1>=1.0.30
.include "../../devel/libusb1/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "aarch64"
PKGREVISION=	1	# Reissue the withdrawn AArch64 package.
.endif
.include "../../mk/bsd.pkg.mk"
