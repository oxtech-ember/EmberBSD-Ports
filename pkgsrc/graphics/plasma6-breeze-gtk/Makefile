# $NetBSD: Makefile,v 1.7 2026/09/06 10:23:29 markd Exp $

DISTNAME=	breeze-gtk-${PLASMAVER}
CATEGORIES=	graphics

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Breeze widget theme for GTK 2 and 3
LICENSE=	gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/plasma6.mk"

TOOL_DEPENDS+=	sassc-[0-9]*:../../www/sassc
TOOL_DEPENDS+=	${PYPKGPREFIX}-cairo-[0-9]*:../../graphics/py-cairo

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
_BREEZE_COLORS=	${EMBERBSD_CROSS_SYSROOT}${PREFIX}/share/color-schemes
.else
_BREEZE_COLORS=	${PREFIX}/share/color-schemes
.endif

pre-configure:
	${RM} -f ${BUILDLINK_DIR}/share/color-schemes
	${LN} -s ${_BREEZE_COLORS} ${BUILDLINK_DIR}/share/color-schemes

.include "../../lang/python/application.mk"
.include "../../lang/python/tool.mk"
.include "../../graphics/plasma6-breeze/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
