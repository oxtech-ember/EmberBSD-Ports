# muffin: Cinnamon's window manager and Wayland compositor
# (mutter fork with in-tree cogl and clutter).
# Cinnamon probe, Wayland profile:
#   - GTK3 server-side decoration stack replaced by no-op stubs
#     (ui.c, frames.h patches); no GTK3 dependency remains.
#   - remote desktop / screencast (PipeWire) disabled.
#   - native DRM backend enabled; libinput comes from libopeninput.
DISTNAME=	17c958413753feafdbd5d58dc1e420f72a5f1859
PKGNAME=	muffin-6.7.9
CATEGORIES=	wm
MASTER_SITES=	https://github.com/linuxmint/muffin/archive/
WRKSRC=		${WRKDIR}/muffin-${DISTNAME}

HOMEPAGE=	https://github.com/linuxmint/muffin
COMMENT=	Cinnamon window manager and Wayland compositor
LICENSE=	gnu-gpl-v2

USE_TOOLS+=	pkg-config msgfmt
USE_LANGUAGES=	c

# Wayland session core; X11 support stays compiled (upstream builds
# both) and runs through Xwayland.
MESON_ARGS+=	-Dopengl=true -Degl=true -Dgles2=true
MESON_ARGS+=	-Dwayland=true
MESON_ARGS+=	-Dnative_backend=true
MESON_ARGS+=	-Dremote_desktop=false
MESON_ARGS+=	-Degl_device=true
MESON_ARGS+=	-Dwayland_eglstream=false
# libudev-bsd provides libudev.pc; meson looks for udev.pc. Input
# hotplug monitoring stays off until the pc alias is wired (recorded).
MESON_ARGS+=	-Dudev=false
MESON_ARGS+=	-Dlibwacom=false
MESON_ARGS+=	-Dstartup_notification=false
MESON_ARGS+=	-Dprofiler=false
MESON_ARGS+=	-Dtests=false -Dinstalled_tests=false
MESON_ARGS+=	-Dcogl_tests=false -Dclutter_tests=false -Dcore_tests=false
# The Xwayland binary lives on the target; meson checks the path exists.
MESON_ARGS+=	-Dxwayland_path=/Volumes/BigData/EmberBSD/work/cinnamon-cross/shims/Xwayland
# cvt runs at build time to generate test mode lines; host shim answers.
MESON_BINARIES+= cvt
MESON_BINARY.cvt= /Volumes/BigData/EmberBSD/work/cinnamon-cross/shims/cvt

# Meta/Clutter/Cogl typelibs are imported by the shell JS at startup.
BUILD_DEPENDS+=	glib2-introspection>=2.90.1nb1:../../devel/glib2-introspection
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
MESON_BINARIES+= g-ir-scanner g-ir-compiler
MESON_BINARY.g-ir-scanner= ${TOOLBASE}/bin/g-ir-scanner
MESON_BINARY.g-ir-compiler= ${TOOLBASE}/bin/g-ir-compiler
MAKE_ENV+= XDG_DATA_DIRS=${CROSS_DESTDIR:Q}${PREFIX:Q}/share

.include "../../devel/glib2/buildlink3.mk"
.include "../../graphics/gdk-pixbuf2/buildlink3.mk"
.include "../../devel/pango/buildlink3.mk"
.include "../../graphics/cairo/buildlink3.mk"
.include "../../fonts/harfbuzz/buildlink3.mk"
.include "../../converters/fribidi/buildlink3.mk"
.include "../../x11/libXau/buildlink3.mk"
.include "../../x11/libXcursor/buildlink3.mk"
.include "../../x11/libXdamage/buildlink3.mk"
.include "../../x11/libXfixes/buildlink3.mk"
.include "../../x11/libXi/buildlink3.mk"
.include "../../x11/libXinerama/buildlink3.mk"
.include "../../x11/libXrandr/buildlink3.mk"
.include "../../x11/libXrender/buildlink3.mk"
.include "../../x11/libXres/buildlink3.mk"
.include "../../x11/libXtst/buildlink3.mk"
.include "../../x11/libxcb/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../textproc/json-glib/buildlink3.mk"
.include "../../x11/cinnamon-desktop/buildlink3.mk"
.include "../../sysutils/gsettings-desktop-schemas/buildlink3.mk"
.include "../../devel/libopeninput/buildlink3.mk"
.include "../../devel/libgudev/buildlink3.mk"
.include "../../devel/libudev-bsd/buildlink3.mk"
.include "../../devel/input-headers/buildlink3.mk"
.include "../../graphics/graphene/buildlink3.mk"
.include "../../x11/libXcomposite/buildlink3.mk"
.include "../../devel/at-spi2-core/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../devel/wayland-protocols/buildlink3.mk"
.include "../../x11/libICE/buildlink3.mk"
.include "../../x11/libSM/buildlink3.mk"
.include "../../graphics/MesaLib/buildlink3.mk"
.include "../../x11/libdrm/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/libXcomposite/buildlink3.mk"
.include "../../devel/at-spi2-core/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../devel/wayland-protocols/buildlink3.mk"
.include "../../x11/libICE/buildlink3.mk"
.include "../../x11/libSM/buildlink3.mk"
.include "../../x11/libXcursor/buildlink3.mk"
.include "../../x11/libXdamage/buildlink3.mk"
.include "../../x11/libXext/buildlink3.mk"
.include "../../x11/libXfixes/buildlink3.mk"
.include "../../x11/libXi/buildlink3.mk"
.include "../../x11/libXinerama/buildlink3.mk"
.include "../../x11/libXrandr/buildlink3.mk"
.include "../../x11/libXrender/buildlink3.mk"
.include "../../x11/libXres/buildlink3.mk"
.include "../../x11/libXtst/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../x11/libxkbfile/buildlink3.mk"
.include "../../x11/libxcb/buildlink3.mk"
.include "../../x11/xkeyboard-config/buildlink3.mk"
.include "../../audio/libcanberra/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
