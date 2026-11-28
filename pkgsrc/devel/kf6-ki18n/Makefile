# $NetBSD: Makefile,v 1.17 2026/09/06 10:05:12 markd Exp $

DISTNAME=	ki18n-${KF6VER}
CATEGORIES=	devel

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Advanced internationalization framework
LICENSE=	modified-bsd AND gnu-lgpl-v2.1

USE_TOOLS+=	msgfmt pkg-config

CMAKE_CONFIGURE_ARGS+=	-DLibIntl_INCLUDE_DIRS=${BUILDLINK_PREFIX.gettext}/include

.include "../../meta-pkgs/kde/kf6.mk"

.if ${OPSYS} == "Darwin" || ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKGREVISION=	1
.endif

.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
# A qt6-qtbase with the host-tools option (the native Qt of a cross build)
# has no Qt Gui, Qt Qml or Qt Test. Build without the QML modules, the
# scripted translations (ktranscript) that need Qt Qml, and the tests.
PLIST_VARS+=	qml
.if ${PKG_BUILD_OPTIONS.qt6-qtbase:Mhost-tools}
CMAKE_CONFIGURE_ARGS+=	-DBUILD_WITH_QML=OFF -DBUILD_TESTING=OFF
.else
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
PLIST.qml=	yes
.endif
.include "../../textproc/iso-codes/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
