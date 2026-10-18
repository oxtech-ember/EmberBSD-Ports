# cinnamon-menus: freedesktop menu library for Cinnamon (CMenu-3.0).
# Cinnamon probe; GIR is required by the shell at runtime.
DISTNAME=	1461debf15c829672f4732b141d11fa00ec50d30
PKGNAME=	cinnamon-menus-6.7.1
CATEGORIES=	x11
MASTER_SITES=	https://github.com/linuxmint/cinnamon-menus/archive/
WRKSRC=		${WRKDIR}/cinnamon-menus-${DISTNAME}

HOMEPAGE=	https://github.com/linuxmint/cinnamon-menus
COMMENT=	Freedesktop menu specification library for Cinnamon
LICENSE=	gnu-lgpl-v2

USE_TOOLS+=	pkg-config
USE_LANGUAGES=	c

# The CMenu-3.0 typelib is imported by the shell JS; introspection
# runs through the shared GI cross machinery with target GType queries.
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
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
