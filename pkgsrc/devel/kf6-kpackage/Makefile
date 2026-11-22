# $NetBSD: Makefile,v 1.17 2026/09/06 10:05:13 markd Exp $

DISTNAME=	kpackage-${KF6VER}
CATEGORIES=	devel

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Installation and loading of additional content as packages
LICENSE=	gnu-gpl-v2 AND gnu-lgpl-v2.1

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes"
PKGREVISION=	1
# CMake removes this build-tree path when it installs kpackagetool6.
BUILDLINK_PASSTHRU_RPATHDIRS+=	${WRKSRC}/${CMAKE_BUILD_DIR}/bin
CMAKE_CONFIGURE_ARGS+=	-DKDE_SKIP_RPATH_SETTINGS=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH="@loader_path/../lib;@loader_path/../qt6/lib"
.endif

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../devel/kf6-kdoctools/tools.mk"

USE_TOOLS+=	msgmerge

.include "../../lang/python/tool.mk"
.include "../../archivers/kf6-karchive/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/qt6-qttools/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes"
# The installed CMake targets already search this prefix relative to the image.
# Keep library link directories and all other linker options from buildlink.
.for _dir in lib qt6/lib qt6/plugins
LDFLAGS:=	${LDFLAGS:N${COMPILER_RPATH_FLAG}${PREFIX}/${_dir}}
.endfor
.endif
