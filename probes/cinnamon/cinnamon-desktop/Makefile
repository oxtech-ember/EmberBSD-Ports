# cinnamon-desktop: schemas and utility library for the Cinnamon session.
# Cinnamon probe, Wayland profile: the GTK3-era background, RandR and
# thumbnail code is not built; the mint27 wallpaper painter lives in the
# cinnamon package itself (GTK4 + layer-shell).
DISTNAME=	6c6c48d7c87359b34b5812486d364fde3ed730ed
PKGNAME=	cinnamon-desktop-6.7.9
CATEGORIES=	x11
MASTER_SITES=	https://github.com/linuxmint/cinnamon-desktop/archive/
WRKSRC=		${WRKDIR}/cinnamon-desktop-${DISTNAME}

HOMEPAGE=	https://github.com/linuxmint/cinnamon-desktop
COMMENT=	Shared settings and utilities for the Cinnamon desktop
LICENSE=	gnu-lgpl-v2

USE_TOOLS+=	pkg-config msgfmt
USE_LANGUAGES=	c


# The CinnamonDesktop-3.0 and CDesktopEnums-3.0 typelibs are imported
# by the shell JS (wall clock, keybindings).
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
.include "../../textproc/iso-codes/buildlink3.mk"
.include "../../x11/libXext/buildlink3.mk"
.include "../../x11/libxkbfile/buildlink3.mk"
.include "../../fonts/fontconfig/buildlink3.mk"
.include "../../devel/libudev-bsd/buildlink3.mk"
# libcvc (mint27 volume control for the shell) needs libpulse.
.include "../../audio/pulseaudio/buildlink3.mk"
.include "../../x11/xkeyboard-config/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
