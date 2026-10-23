# $NetBSD: Makefile,v 1.21 2026/09/02 19:04:29 wiz Exp $
.include "../../mk/bsd.prefs.mk"

DISTNAME=	gsettings-desktop-schemas-51.0
CATEGORIES=	sysutils gnome
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/gsettings-desktop-schemas/${PKGVERSION_NOREV:R}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.gnome.org/
COMMENT=	Collection of GSettings schemas for the GNOME desktop
LICENSE=	gnu-lgpl-v2.1

USE_TOOLS+=		msgfmt pkg-config

PKGCONFIG_OVERRIDE+=	gsettings-desktop-schemas.pc.in

PYTHON_FOR_BUILD_ONLY=	tool

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
MESON_BINARIES+= glib-mkenums
MESON_BINARY.glib-mkenums= ${TOOLBASE}/bin/glib-mkenums
.endif

.include "../../devel/glib2/schemas.mk"
# The complete desktop profile retains the GDesktopEnums bindings.
PLIST_VARS+= introspection
PLIST.introspection= yes
MESON_ARGS+= -Dintrospection=true
BUILDLINK_DEPMETHOD.gobject-introspection:=	build
BUILDLINK_API_DEPENDS.gobject-introspection+=	gobject-introspection>=1.31
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"
