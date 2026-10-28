# $NetBSD: Makefile,v 1.38 2026/09/02 19:01:43 wiz Exp $

DISTNAME=	qttools-everywhere-src-${QTVERSION}
PKGNAME=	qt6-qttools-${QTVERSION}
PKGREVISION=	3
COMMENT=	Qt6 development tools
CATEGORIES=	devel
LICENSE=	gnu-lgpl-v3 OR gnu-gpl-v2 OR gnu-gpl-v3

.include "../../x11/qt6-qtbase/Makefile.common"

# The lupdate test data has a UTF-8 file name (parseqrc/café.js).
# bsdtar cannot write it in the C locale of the Ports make environment.
EXTRACT_ENV+=	LC_ALL=C.UTF-8

PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Designer.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Help.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6UiTools.pc

# Use the repaired common HTML provider; never embed another litehtml copy.
CMAKE_CONFIGURE_ARGS+= -DQLITEHTML_USE_SYSTEM_LITEHTML=ON
# Runtime package without libclang: QDoc is the only libclang consumer.
# Lupdate keeps its built-in C++ parser. Desktop closures stay free of the
# Clang and LLVM SDK packages.
CMAKE_CONFIGURE_ARGS+= -DFEATURE_clang=OFF -DFEATURE_qdoc=OFF
CMAKE_CONFIGURE_ARGS+= -DCMAKE_DISABLE_FIND_PACKAGE_WrapLibClang=ON

.include "options.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && defined(EMBERBSD_QT_HOST_PATH)
# Cross builds import the matching host Linguist and Tools tool packages.
CMAKE_CONFIGURE_ARGS+= -DQt6LinguistTools_DIR=${EMBERBSD_QT_HOST_PATH:Q}/lib/cmake/Qt6LinguistTools
CMAKE_CONFIGURE_ARGS+= -DQt6ToolsTools_DIR=${EMBERBSD_QT_HOST_PATH:Q}/lib/cmake/Qt6ToolsTools
.endif

# Designer resource compression uses libzstd directly.
.include "../../archivers/zstd/buildlink3.mk"
.if empty(PKG_OPTIONS:Mhost-tools)
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../www/litehtml/buildlink3.mk"
.endif
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
