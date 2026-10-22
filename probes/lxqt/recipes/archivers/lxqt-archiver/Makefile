# $NetBSD: Makefile,v 1.48 2026/09/02 19:00:42 wiz Exp $

PKGREVISION= 3
.include "../../meta-pkgs/lxqt/Makefile.common"

DISTNAME=	lxqt-archiver-1.4.0
CATEGORIES=	archivers

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/lxqt/lxqt-archiver/
COMMENT=	Simple and lightweight Qt file archiver
LICENSE=	gnu-gpl-v2

USE_TOOLS+=	pkg-config perl

DEPENDS+=	7-zip>=26.03:../../archivers/7-zip
DEPENDS+=	bsdtar-[0-9]*:../../archivers/bsdtar
DEPENDS+=	bzip2>=1.0.8:../../archivers/bzip2
DEPENDS+=	gtar-base>=1.35:../../archivers/gtar-base
DEPENDS+=	gzip>=1.14:../../archivers/gzip
DEPENDS+=	unzip-[0-9]*:../../archivers/unzip
DEPENDS+=	zip-[0-9]*:../../archivers/zip
DEPENDS+=	xz>=5.8.4:../../archivers/xz

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_PREFIX=${PREFIX}

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.include "../../meta-pkgs/lxqt/host-modules.mk"
.include "../../meta-pkgs/lxqt/host-tools.mk"
.else
TOOL_DEPENDS+=	lxqt-build-tools>=2.4.0:../../devel/lxqt-build-tools
TOOL_DEPENDS+=	qt6-qttools-[0-9]*:../../devel/qt6-qttools
.endif

BUILDLINK_API_DEPENDS.qt6-qtbase+=      qt6-qtbase>=6.6.0
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../x11/libfm-qt/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../textproc/json-glib/buildlink3.mk"
.include "../../x11/xcb-util-cursor/buildlink3.mk"
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
