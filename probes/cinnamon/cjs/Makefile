# cjs: Cinnamon's JavaScript bindings (gjs fork on SpiderMonkey 140).
# Cinnamon probe; pinned to the mint27 branch line that carries the
# Wayland-complete Cinnamon 6.8 development state.
DISTNAME=	84e7840ce148b75f9d38b57d82cdc9a47dd3a7eb
PKGNAME=	cjs-140.1
CATEGORIES=	lang
MASTER_SITES=	https://github.com/linuxmint/cjs/archive/
WRKSRC=		${WRKDIR}/cjs-${DISTNAME}

HOMEPAGE=	https://github.com/linuxmint/cjs
COMMENT=	JavaScript bindings for Cinnamon (SpiderMonkey 140)
LICENSE=	mit AND gnu-lgpl-v2

USE_TOOLS+=	pkg-config
USE_LANGUAGES=	c c++

# SpiderMonkey embedders must declare the target platform themselves
# (mozilla/UniquePtrExtensions.h needs XP_UNIX for FileHandleType).
CPPFLAGS+=	-DXP_UNIX
# NetBSD feature macros: uselocale(3) needs _NETBSD_SOURCE with -std=c99.
CPPFLAGS+=	-D_NETBSD_SOURCE

# meson project defaults: cpp_std=c++17, RTTI and exceptions off,
# matching the SpiderMonkey build configuration.
MESON_ARGS+=	-Dprofiler=disabled
MESON_ARGS+=	-Dinstalled_tests=false
MESON_ARGS+=	-Dskip_gtk_tests=true
MESON_ARGS+=	-Dskip_dbus_tests=true

# No GTK is linked into cjs on this profile; the shell loads GTK
# typelibs at runtime instead. cairo stays: the shell uses the
# cairo GI module.

# GjsPrivate-1.0 GIR/typelib generation goes through the shared GI
# cross machinery; target GType queries run on the CM5 query host.
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
.include "../../graphics/cairo/buildlink3.mk"
.include "../../devel/libffi/buildlink3.mk"
.include "../../lang/mozjs140/buildlink3.mk"
.include "../../mk/readline.buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
