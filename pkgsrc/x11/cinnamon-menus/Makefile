# cinnamon-menus: freedesktop menu library for Cinnamon (CMenu-3.0).
# GIR is required by the shell at runtime.
DISTNAME=	cinnamon-menus-6.6.0
PKGREVISION=4
CATEGORIES=	x11
MASTER_SITES=	https://github.com/linuxmint/cinnamon-menus/archive/refs/tags/
DISTFILES=	6.6.0.tar.gz
WRKSRC=		${WRKDIR}/${DISTNAME}

HOMEPAGE=	https://github.com/linuxmint/cinnamon-menus
COMMENT=	Freedesktop menu specification library for Cinnamon
LICENSE=	gnu-lgpl-v2

USE_TOOLS+=	pkg-config
USE_LANGUAGES=	c

# The CMenu-3.0 typelib is imported by the shell JS; introspection
# runs through the shared GI cross machinery with target GType queries.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
BUILD_DEPENDS+= glib2-introspection>=2.90.1nb1:../../devel/glib2-introspection
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
MESON_BINARIES+= g-ir-scanner g-ir-compiler
MESON_BINARY.g-ir-scanner= ${TOOLBASE}/bin/g-ir-scanner
MESON_BINARY.g-ir-compiler= ${TOOLBASE}/bin/g-ir-compiler
MAKE_ENV+= XDG_DATA_DIRS=${CROSS_DESTDIR:Q}${PREFIX:Q}/share
.else
TOOL_DEPENDS+= glib2-introspection-[0-9]*:../../devel/glib2-introspection
.endif

BUILDLINK_API_DEPENDS.glib2+= glib2>=2.82.0
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
