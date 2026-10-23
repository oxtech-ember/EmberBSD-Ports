# $NetBSD: Makefile,v 1.19 2026/09/06 10:05:19 markd Exp $

DISTNAME=	kholidays-${KF6VER}
CATEGORIES=	time

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	KDE library for regional holiday information
LICENSE=	gnu-lgpl-v2

.include "../../meta-pkgs/kde/kf6.mk"

USE_TOOLS+=	bison gm4 msgmerge
# Apple flex 2.6.4 has a different C++ scanner ABI from the upstream header.
# Only the generator is needed; KHolidays supplies its scanner header and yywrap.
TOOL_DEPENDS+= flex>=2.6.4:../../devel/flex
CMAKE_CONFIGURE_ARGS+= -DFLEX_EXECUTABLE=${TOOLBASE:Q}/bin/flex

.include "../../devel/qt6-qttools/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
