# $NetBSD: Makefile,v 1.16 2026/09/06 10:05:11 markd Exp $

DISTNAME=	karchive-${KF6VER}
PKGREVISION=	1
CATEGORIES=	archivers

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Qt 6 addon providing access to numerous types of archives
LICENSE=	gnu-gpl-v2 AND gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/kf6.mk"

USE_TOOLS+=	pkg-config

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# CMake validates imported pkg-config include paths on the build host.
CONFIGURE_ENV+= PKG_CONFIG_SYSROOT_DIR=${CROSS_DESTDIR}
.endif

PKGCONFIG_OVERRIDE+=		_KDE_build/KF6Archive.pc
PKGCONFIG_OVERRIDE_STAGE=	post-build

.include "../../archivers/bzip2/buildlink3.mk"
.include "../../archivers/xz/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/qt6-qttools/linguist.mk"
.include "../../mk/bsd.pkg.mk"
