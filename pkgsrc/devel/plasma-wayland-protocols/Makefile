# $NetBSD: Makefile,v 1.26 2026/09/06 09:34:38 markd Exp $

DISTNAME=	plasma-wayland-protocols-1.23.0
PKGREVISION=	1
CATEGORIES=	devel kde
MASTER_SITES=	${MASTER_SITE_KDE:=plasma-wayland-protocols/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/kde/plasma-wayland-protocols
COMMENT=	Plasma Specific Protocols for Wayland
LICENSE=	gnu-lgpl-v2.1

USE_LANGUAGES=	c c++

.include "../../devel/cmake/build.mk"

BUILDLINK_API_DEPENDS.extra-cmake-modules+=	extra-cmake-modules>=5.60.0
.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	2	# Reissue: the earlier amd64 name is in a released record.
.endif
.include "../../mk/bsd.pkg.mk"
