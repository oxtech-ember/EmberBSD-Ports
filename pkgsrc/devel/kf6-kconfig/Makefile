# $NetBSD: Makefile,v 1.17 2026/09/06 10:05:11 markd Exp $

.include "Makefile.common"
PKGREVISION=	1

COMMENT=	Configuration system

.include "../../meta-pkgs/kde/kf6.mk"

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF

.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/qt6-qttools/linguist.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
