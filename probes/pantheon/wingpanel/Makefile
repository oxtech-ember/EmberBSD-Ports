# $NetBSD$

DISTNAME=	wingpanel-8.0.4
CATEGORIES=	x11
MASTER_SITES=	${MASTER_SITE_GITHUB:=elementary/}
GITHUB_RELEASE=	8.0.4

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/elementary/wingpanel
COMMENT=	Elementary top panel (GTK4 port for EmberBSD)
LICENSE=	gnu-gpl-v3

USE_TOOLS+=	pkg-config msgfmt tar

# EmberBSD GTK4 port: upstream 8.0.4 is still GTK3; the patches move the
# panel to GTK4 + granite-7 ahead of the upstream migration.

# The 8.0.4 tarball bundles mutter vapis only up to 16; take the mutter-17
# set from the gala tarball that is already in DISTDIR.
post-extract:
	${RUN}cd ${WRKDIR} && ${TAR} -xzf /private/tmp/ember-common-stack/distfiles/gala-8.6.2.tar.gz gala-8.6.2/vapi && ${CP} gala-8.6.2/vapi/*17* ${WRKSRC}/vapi/

.include "../../mk/bsd.prefs.mk"

.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/libgee/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../x11/gtk4/buildlink3.mk"
.include "../../x11/granite/buildlink3.mk"
.include "../../x11/mutter/buildlink3.mk"
.include "../../x11/gala/buildlink3.mk"
.include "../../devel/at-spi2-core/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../graphics/glycin/buildlink3.mk"
.include "../../inputmethod/ibus/buildlink3.mk"
.include "../../x11/gnome-desktop4/buildlink3.mk"
.include "../../x11/libei/buildlink3.mk"
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
.include "../../x11/libX11/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
