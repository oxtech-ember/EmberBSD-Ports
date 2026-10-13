# $NetBSD: Makefile,v 1.32 2026/09/02 19:03:02 wiz Exp $

DISTNAME=	fcitx5-5.1.23
CATEGORIES=	inputmethod
MASTER_SITES=	https://download.fcitx-im.org/fcitx5/fcitx5/
EXTRACT_SUFX=	.tar.zst

MAINTAINER=	ryoon@NetBSD.org
HOMEPAGE=	https://github.com/fcitx/fcitx5
COMMENT=	Input method framework with extension support
LICENSE=	gnu-lgpl-v2.1

DATAFILES+=	en_dict-20121020.tar.gz
EXTRACT_ONLY=	${DEFAULT_DISTFILES}
DISTFILES+=	${DISTNAME}${EXTRACT_SUFX}

.for f in ${DATAFILES}
SITES.${f}=	https://download.fcitx-im.org/data/
DISTFILES+=	${f}
.endfor

SUBST_CLASSES+=			fix-machine-id
SUBST_STAGE.fix-machine-id=	pre-configure
SUBST_MESSAGE.fix-machine-id=	Fixing machine-id path
SUBST_FILES.fix-machine-id+=	src/lib/fcitx/misc_p.h
SUBST_SED.fix-machine-id+=	-e 's,/var/lib/dbus/machine-id,${VARBASE}/lib/dbus/machine-id,g'

CONFLICTS+=	fcitx-[0-9]*

USE_TOOLS+=		pkg-config
DEPENDS+=		bash>=5.3:../../shells/bash
USE_PKGLOCALEDIR=	yes
USE_LANGUAGES=		c c++

CMAKE_CONFIGURE_ARGS+= -DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+= -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
BUILD_DEFS+=		VARBASE

USE_CXX_FEATURES+=	c++20

REPLACE_INTERPRETER+=		target-bash
REPLACE.target-bash.old=		.*sh
REPLACE.target-bash.new=		${PREFIX}/bin/bash
REPLACE_FILES.target-bash=	data/fcitx5-diagnose.sh

CMAKE_CONFIGURE_ARGS+=	-DENABLE_WAYLAND=ON
CMAKE_CONFIGURE_ARGS+=	-DUSE_SYSTEMD=off
CMAKE_CONFIGURE_ARGS+=	-DENABLE_TEST=ON
CMAKE_CONFIGURE_ARGS+=	-DENABLE_TESTING_ADDONS=ON
CMAKE_CONFIGURE_ARGS+=	-DEVENT_LOOP_BACKEND=libuv
CMAKE_CONFIGURE_ARGS+=	-DENABLE_ENCHANT=ON
CMAKE_CONFIGURE_ARGS+=	-DUSE_SYSTEM_PLASMA_WAYLAND_PROTOCOLS=ON
CMAKE_CONFIGURE_ARGS+=	-DLibIntl_INCLUDE_DIR=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.gettext}/include
CMAKE_CONFIGURE_ARGS+=	-DLIBUUID_INCLUDE_DIR=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.libuuid}/include

BUILDLINK_TRANSFORM.SunOS+=	rm:-Wl,--as-needed

PKGCONFIG_OVERRIDE+=	src/lib/fcitx-config/Fcitx5Config.pc.in
PKGCONFIG_OVERRIDE+=	src/lib/fcitx-utils/Fcitx5Utils.pc.in
PKGCONFIG_OVERRIDE+=	src/lib/fcitx/Fcitx5Core.pc.in
PKGCONFIG_OVERRIDE+=	src/modules/Fcitx5Module.pc.in

SUBST_CLASSES+=		xdg
SUBST_STAGE.xdg=	pre-configure
SUBST_MESSAGE.xdg=	Fix desktop autostart file installation
SUBST_FILES.xdg=	data/CMakeLists.txt
SUBST_SED.xdg=		-e 's,{CMAKE_INSTALL_FULL_SYSCONFDIR}/xdg/autostart,{CMAKE_INSTALL_PREFIX}/share/examples/fcitx5,'

MAKE_DIRS+=	${PKG_SYSCONFDIR}/xdg/autostart
CONF_FILES+=	${PREFIX}/share/examples/fcitx5/org.fcitx.Fcitx5.desktop \
		${PKG_SYSCONFDIR}/xdg/autostart/org.fcitx.Fcitx5.desktop

# The target spell compiler remains installed. A matching native compiler
# generates build data during cross compilation.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if !defined(EMBERBSD_FCITX5_COMP_SPELL_DICT) || empty(EMBERBSD_FCITX5_COMP_SPELL_DICT:M/*) || !exists(${EMBERBSD_FCITX5_COMP_SPELL_DICT})
PKG_FAIL_REASON+= "Cross Fcitx5 requires a native 5.1.23 EMBERBSD_FCITX5_COMP_SPELL_DICT"
.else
CMAKE_CONFIGURE_ARGS+= -DFCITX5_HOST_COMP_SPELL_DICT:FILEPATH=${EMBERBSD_FCITX5_COMP_SPELL_DICT:Q}
.endif
.if !defined(EMBERBSD_WAYLAND_SCANNER) || empty(EMBERBSD_WAYLAND_SCANNER:M/*) || !exists(${EMBERBSD_WAYLAND_SCANNER})
PKG_FAIL_REASON+= "Cross Fcitx5 requires the current native EMBERBSD_WAYLAND_SCANNER"
.else
CMAKE_CONFIGURE_ARGS+= -DWaylandScanner_EXECUTABLE:FILEPATH=${EMBERBSD_WAYLAND_SCANNER:Q}
.endif
.endif

pre-configure:
	${LN} -s ${DISTDIR}/en_dict-20121020.tar.gz \
		${WRKSRC}/src/modules/spell/

.include "../../devel/cmake/build.mk"

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../devel/gettext-tools/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/libexecinfo/buildlink3.mk"
.include "../../devel/libuuid/buildlink3.mk"
.include "../../devel/libuv/buildlink3.mk"
.include "../../devel/pango/buildlink3.mk"
.include "../../graphics/cairo/buildlink3.mk"
.include "../../graphics/gdk-pixbuf2/buildlink3.mk"
.include "../../graphics/librsvg/buildlink3.mk"
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
.include "../../sysutils/dbus/buildlink3.mk"
.include "../../sysutils/desktop-file-utils/desktopdb.mk"
.include "../../textproc/enchant2/buildlink3.mk"
.include "../../textproc/expat/buildlink3.mk"
.include "../../textproc/iso-codes/buildlink3.mk"
.include "../../textproc/nlohmann-json/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../devel/wayland-protocols/buildlink3.mk"
.include "../../devel/plasma-wayland-protocols/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../x11/libxcb/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../x11/libxkbfile/buildlink3.mk"
.include "../../x11/xcb-imdkit/buildlink3.mk"
.include "../../x11/xcb-util/buildlink3.mk"
.include "../../x11/xcb-util-keysyms/buildlink3.mk"
.include "../../x11/xcb-util-wm/buildlink3.mk"
.include "../../x11/xkeyboard-config/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
