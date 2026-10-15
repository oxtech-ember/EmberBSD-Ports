# $NetBSD: Makefile,v 1.16 2026/09/06 10:05:20 markd Exp $

DISTNAME=	kded-${KF6VER}
PKGREVISION=	1
CATEGORIES=	x11

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Extensible deamon for providing system level services
LICENSE=	gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/kf6.mk"

# Cross builds resolve KF6::kconf_update and the kconfig compiler through
# the shared native host tooling (cross/build-kconfig-tool.sh).
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CMAKE_CONFIGURE_ARGS+= -DKF6_HOST_TOOLING=${EMBERBSD_KF6_HOST_TOOLING}
pre-configure:
	${TEST} -x ${EMBERBSD_KF6_HOST_TOOLING}/bin/kconf_update
.endif

.include "../../devel/kf6-kdoctools/tools.mk"

.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-kservice/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
