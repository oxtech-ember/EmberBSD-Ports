# Compositor and window manager library for GNOME and Pantheon.
# Probe recipe for the Pantheon port (project debt E25): fetch, extract,
# patch and static-analysis delta were validated on 2026-10-12; the
# native build has not run yet. Current pairing: mutter 49.8 provides
# libmutter-17, which the current gala 8.6.2 declares support for.
DISTNAME=	mutter-49.8
CATEGORIES=	x11
MASTER_SITES=	https://download.gnome.org/sources/mutter/49/
EXTRACT_SUFX=	.tar.xz

HOMEPAGE=	https://gitlab.gnome.org/GNOME/mutter
COMMENT=	Compositor and window manager library (libmutter-17)
LICENSE=	gnu-gpl-v2

USE_TOOLS+=	pkg-config msgfmt

# NetBSD has no systemd/elogind in this profile; session detection
# falls back to XDG_SESSION_TYPE through the context patch. The udev
# backend is tied to logind upstream, so it stays off for this probe;
# input comes through libopeninput and seatd instead.
MESON_ARGS+=	-Dlogind=false
# NetBSD has no logind/udev; the native (DRM) backend requires both.
MESON_ARGS+=	-Dnative_backend=false
MESON_ARGS+=	-Dudev=false
# Wayland-only profile: X11 apps run through Xwayland; gtk3 drops out.
MESON_ARGS+=	-Dx11=false
MESON_ARGS+=	-Dremote_desktop=false
MESON_ARGS+=	-Dlibwacom=false
MESON_ARGS+=	-Dsound_player=false
MESON_ARGS+=	-Ddocs=false
MESON_ARGS+=	-Dtests=disabled
MESON_ARGS+=	-Dstartup_notification=false
MESON_ARGS+=	-Dprofiler=false
# The Xwayland binary lives on the target, not on the cross host.
MESON_ARGS+=	-Dxwayland_path=/usr/X11R7/bin/Xwayland
MESON_ARGS+=	-Dbash_completion=false

.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
# libopeninput provides the libinput pkg-config module on NetBSD.
.include "../../devel/libopeninput/buildlink3.mk"
.include "../../textproc/json-glib/buildlink3.mk"
.include "../../devel/meson/build.mk"

# The meson-generated python tools use /usr/bin/env shebangs.
post-install:
	${RUN}${SED} -e '1s|^#!.*python.*|#!${PREFIX}/bin/python3.14|' \
		-i ${DESTDIR}${PREFIX}/bin/gdctl ${DESTDIR}${PREFIX}/bin/gnome-service-client
.include "../../sysutils/gsettings-desktop-schemas/buildlink3.mk"
.include "../../x11/gtk4/buildlink3.mk"
.include "../../x11/libXcomposite/buildlink3.mk"
.include "../../x11/libXcursor/buildlink3.mk"
.include "../../x11/libXdamage/buildlink3.mk"
.include "../../x11/libXext/buildlink3.mk"
.include "../../x11/libXfixes/buildlink3.mk"
.include "../../x11/libXi/buildlink3.mk"
.include "../../x11/libXinerama/buildlink3.mk"
.include "../../x11/libXrandr/buildlink3.mk"
.include "../../x11/libxcb/buildlink3.mk"
.include "../../x11/libXau/buildlink3.mk"
.include "../../x11/xkeyboard-config/buildlink3.mk"
.include "../../x11/gnome-desktop4/buildlink3.mk"
.include "../../graphics/cairo/buildlink3.mk"
.include "../../graphics/graphene/buildlink3.mk"
.include "../../graphics/gdk-pixbuf2/buildlink3.mk"
.include "../../graphics/colord/buildlink3.mk"
.include "../../graphics/glycin/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../devel/at-spi2-core/buildlink3.mk"
.include "../../graphics/lcms2/buildlink3.mk"
.include "../../x11/libei/buildlink3.mk"
.include "../../x11/libdrm/buildlink3.mk"
.include "../../x11/pixman/buildlink3.mk"
.include "../../x11/libdisplay-info/buildlink3.mk"
.include "../../devel/pango/buildlink3.mk"
.include "../../fonts/harfbuzz/buildlink3.mk"
.include "../../sysutils/gsettings-desktop-schemas/buildlink3.mk"
# Remaining links (wayland stack, libdrm, xkbcommon, X client libraries,
# gnome-desktop-4 and its gnome-bg-4 module) are finalized together with
# the first build pass of this probe.
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
