# $NetBSD: Makefile,v 1.16 2026/09/06 10:05:14 markd Exp $

DISTNAME=	kpty-${KF6VER}
CATEGORIES=	devel

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Pty abstraction
LICENSE=	gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/kf6.mk"

.if ${USE_CROSS_COMPILE:Uno} == "yes" && ${MACHINE_ARCH} == "aarch64" && ${OPSYS} == "NetBSD"
PKGREVISION=	1 # Refresh base libutil requirements to the stable SONAME.
.endif

# libutempter is not ported; KPty sessions build without utmp records.
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_UTEMPTER:BOOL=TRUE

USE_TOOLS+=	msgmerge

CFLAGS.SunOS+=	-D__EXTENSIONS__

.include "../../lang/python/tool.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
