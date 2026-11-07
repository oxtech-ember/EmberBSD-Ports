# $NetBSD$

DISTNAME=	kquickimageeditor-0.7.0.1
CATEGORIES=	graphics
MASTER_SITES=	${MASTER_SITE_KDE:=kquickimageeditor/}
EXTRACT_SUFX=	.tar.xz

HOMEPAGE=	https://invent.kde.org/libraries/kquickimageeditor
COMMENT=	Qt Quick image editor used by Spectacle
LICENSE=	gnu-lgpl-v2.1

USE_CXX_FEATURES+=	c++23
USE_TOOLS+=	pkg-config
# The image editor includes Highway headers in one translation unit.
# The cross compiler does not enable the matching x86 features there.
# The portable Highway target keeps the editor working on this CPU.
CPPFLAGS+=	-DHWY_COMPILE_ONLY_EMU128

.include "../../meta-pkgs/kde/Makefile.common"

CMAKE_CONFIGURE_ARGS+=	-DKDE_INSTALL_QMLDIR=qt6/qml
CMAKE_CONFIGURE_ARGS+=	-DKDE_INSTALL_QTPLUGINDIR=qt6/plugins

.include "../../devel/highway/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../graphics/qt6-qtshadertools/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
