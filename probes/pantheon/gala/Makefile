# elementary gala: the Pantheon window manager built on libmutter.
# Probe recipe for the Pantheon port (E25): distfile hashed on
# 2026-10-12; build not yet run. Current release, pairs with
# libmutter-17 (mutter 49.8) selected by its meson probe.
DISTNAME=	gala-8.6.2
CATEGORIES=	x11
MASTER_SITES=	${MASTER_SITE_GITHUB:=elementary/}
GITHUB_RELEASE=	8.6.2

HOMEPAGE=	https://github.com/elementary/gala
COMMENT=	Pantheon window and compositing manager on libmutter
LICENSE=	gnu-gpl-v3

USE_TOOLS+=	pkg-config msgfmt

MESON_ARGS+=	-Dsystemd=false

.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/libgee/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../inputmethod/ibus/buildlink3.mk"
.include "../../x11/granite/buildlink3.mk"
.include "../../x11/gnome-desktop4/buildlink3.mk"
.include "../../x11/gtk4/buildlink3.mk"
.include "../../x11/mutter/buildlink3.mk"
.include "../../devel/at-spi2-core/buildlink3.mk"
.include "../../databases/sqlite3/buildlink3.mk"
.include "../../graphics/lcms2/buildlink3.mk"
.include "../../x11/libdisplay-info/buildlink3.mk"
.include "../../x11/libXcomposite/buildlink3.mk"
.include "../../x11/libXdamage/buildlink3.mk"
.include "../../x11/libXrandr/buildlink3.mk"
.include "../../x11/libXinerama/buildlink3.mk"
.include "../../x11/libXcursor/buildlink3.mk"
.include "../../x11/libXext/buildlink3.mk"
.include "../../x11/libXfixes/buildlink3.mk"
.include "../../x11/libXi/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../x11/libdrm/buildlink3.mk"
.include "../../x11/pixman/buildlink3.mk"
.include "../../x11/libei/buildlink3.mk"
.include "../../graphics/glycin/buildlink3.mk"
.include "../../devel/pango/buildlink3.mk"
.include "../../fonts/harfbuzz/buildlink3.mk"
.include "../../devel/libopeninput/buildlink3.mk"
.include "../../graphics/cairo/buildlink3.mk"
.include "../../graphics/colord/buildlink3.mk"
.include "../../graphics/gdk-pixbuf2/buildlink3.mk"
.include "../../graphics/graphene/buildlink3.mk"
.include "../../sysutils/gsettings-desktop-schemas/buildlink3.mk"
.include "../../textproc/json-glib/buildlink3.mk"
.include "../../x11/libxcb/buildlink3.mk"
.include "../../x11/xkeyboard-config/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
