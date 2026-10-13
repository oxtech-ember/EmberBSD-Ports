# $NetBSD: Makefile,v 1.16 2026/09/06 10:05:19 markd Exp $

DISTNAME=	syntax-highlighting-${KF6VER}
CATEGORIES=	textproc

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Syntax highlighting engine for structured text and code
LICENSE=	gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/kf6.mk"

# Cross builds use the native katehighlightingindexer built by
# cross/build-syntax-indexer-host.sh; upstream accepts the executable
# through KATEHIGHLIGHTINGINDEXER_EXECUTABLE.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CMAKE_CONFIGURE_ARGS+= -DKATEHIGHLIGHTINGINDEXER_EXECUTABLE=${EMBERBSD_KF6_HOST_TOOLING}/bin/katehighlightingindexer
pre-configure:
	${TEST} -x ${EMBERBSD_KF6_HOST_TOOLING}/bin/katehighlightingindexer
.endif

USE_TOOLS+=	perl pkg-config

CHECK_PORTABILITY_SKIP+=	autotests/input/highlight.sh
CHECK_PORTABILITY_SKIP+=	autotests/folding/highlight.sh.fold

.include "../../devel/qt6-qttools/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../textproc/xerces-c/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"
