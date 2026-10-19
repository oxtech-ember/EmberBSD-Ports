# cjs: Cinnamon's JavaScript bindings (gjs fork on SpiderMonkey 140).
# Use the stable CJS 140.1 tag from the Cinnamon 6.6 source set.
DISTNAME=	cjs-140.1
DISTFILES=	140.1.tar.gz
SITES.140.1.tar.gz=	-https://github.com/linuxmint/cjs/archive/refs/tags/140.1.tar.gz
PKGREVISION=1
CATEGORIES=	lang
WRKSRC=		${WRKDIR}/cjs-140.1

HOMEPAGE=	https://github.com/linuxmint/cjs
COMMENT=	JavaScript bindings for Cinnamon (SpiderMonkey 140)
LICENSE=	mit AND gnu-lgpl-v2

USE_TOOLS+=	pkg-config
# The gobject-introspection-tests subproject GIRs are test fixtures;
# building only the install targets skips their scanner invocations
# (the cross wrapper rewrites sysroot -I paths for its cpp pass).
BUILD_TARGET=	install
USE_LANGUAGES=	c c++

# SpiderMonkey embedders must declare the target platform themselves
# (mozilla/UniquePtrExtensions.h needs XP_UNIX for FileHandleType).
CPPFLAGS+=	-DXP_UNIX
# NetBSD feature macros expose the locale_t and *_l interfaces with -std=c99.
CPPFLAGS+=	-D_NETBSD_SOURCE
# EmberBSD libc has no uselocale(3). Do not emulate thread selection by
# returning LC_GLOBAL_LOCALE: report ENOTSUP for setters and preserve queries.
CPPFLAGS+=	-DEMBERBSD_NO_USELOCALE

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
