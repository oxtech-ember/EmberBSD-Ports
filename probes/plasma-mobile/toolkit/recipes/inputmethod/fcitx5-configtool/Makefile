# $NetBSD: Makefile,v 1.33 2026/09/02 19:03:02 wiz Exp $

DISTNAME=	fcitx5-configtool-5.1.16
PKGREVISION=	1
CATEGORIES=	inputmethod
MASTER_SITES=	https://download.fcitx-im.org/fcitx5/fcitx5-configtool/
EXTRACT_SUFX=	.tar.zst

MAINTAINER=	ryoon@NetBSD.org
HOMEPAGE=	https://github.com/fcitx/fcitx5-configtool
COMMENT=	Config tool for fcitx5
LICENSE=	gnu-gpl-v2

USE_PKGLOCALEDIR=	yes
USE_LANGUAGES=		c c++

CMAKE_CONFIGURE_ARGS+= -DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+= -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
# Keep target data locations separate from configure-time sysroot paths.
.for code in 2 3 5
CMAKE_CONFIGURE_ARGS+= -DISOCODES_ISO639_${code}_JSON_RUNTIME:FILEPATH=${BUILDLINK_PREFIX.iso-codes:U${PREFIX}}/share/iso-codes/json/iso_639-${code}.json
.endfor
CMAKE_CONFIGURE_ARGS+= -DXKEYBOARDCONFIG_XKBBASE_RUNTIME:PATH=${BUILDLINK_PREFIX.xkeyboard-config:U${PREFIX}}/share/X11/xkb
USE_TOOLS+=		msgfmt msgmerge pkg-config
# FindGettext runs these host tools during configuration and the build.
CMAKE_CONFIGURE_ARGS+= -DGETTEXT_MSGFMT_EXECUTABLE:FILEPATH=${TOOLS_PATH.msgfmt:Q}
CMAKE_CONFIGURE_ARGS+= -DGETTEXT_MSGMERGE_EXECUTABLE:FILEPATH=${TOOLS_PATH.msgmerge:Q}

# Match the common KF6/Plasma plugin root for the System Settings KCM.
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTPLUGINDIR=qt6/plugins
CMAKE_CONFIGURE_ARGS+= -DENABLE_KCM=ON
CMAKE_CONFIGURE_ARGS+= -DENABLE_CONFIG_QT=ON
# Upstream Configtool defines no test target; input/UI acceptance is separate.

.include "../../devel/cmake/build.mk"

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kdeclarative/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kpackage/buildlink3.mk"
.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/gettext-tools/buildlink3.mk"
.include "../../graphics/kf6-kiconthemes/buildlink3.mk"
.include "../../graphics/kf6-ksvg/buildlink3.mk"
.include "../../graphics/qt6-qtsvg/buildlink3.mk"
.include "../../inputmethod/fcitx5-qt/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../textproc/iso-codes/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kf6-kitemviews/buildlink3.mk"
.include "../../x11/kf6-kwidgetsaddons/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../x11/libxkbfile/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../x11/plasma6-libplasma/buildlink3.mk"
.include "../../x11/xkeyboard-config/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
