# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).

DISTNAME=	qtgraphs-everywhere-src-${QTVERSION}
PKGNAME=	qt6-qtgraphs-${QTVERSION}
COMMENT=	Qt6 module for 2D and 3D data visualization
CATEGORIES=	graphics
LICENSE=	gnu-gpl-v3

.include "../../x11/qt6-qtbase/Makefile.common"

PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Graphs.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Graphs2DImpl.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6GraphsWidgets.pc

.include "../../graphics/qt6-qtquick3d/buildlink3.mk"
.include "../../graphics/qt6-qtshadertools/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
