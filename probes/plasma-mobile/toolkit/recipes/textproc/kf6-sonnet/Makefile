# $NetBSD: Makefile,v 1.16 2026/09/06 10:05:19 markd Exp $

DISTNAME=	sonnet-${KF6VER}
PKGREVISION=	2
CATEGORIES=	textproc

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Spelling framework for Qt6
LICENSE=	gnu-lgpl-v2.1

USE_TOOLS+=	pkg-config

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CMAKE_CONFIGURE_ARGS+= -DPARSETRIGRAMS_EXECUTABLE=${EMBERBSD_KF6_HOST_TOOLING}/bin/parsetrigrams6
pre-configure:
	${TEST} -x ${EMBERBSD_KF6_HOST_TOOLING:U/nonexistent:Q}/bin/parsetrigrams6
.endif

.include "../../devel/qt6-qttools/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../textproc/aspell/buildlink3.mk"
.include "../../textproc/hunspell/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
