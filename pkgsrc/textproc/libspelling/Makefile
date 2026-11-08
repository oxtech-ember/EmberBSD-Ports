# $NetBSD: Makefile,v 1.2 2026/09/02 19:04:44 wiz Exp $

DISTNAME=	libspelling-0.4.11
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/libspelling/${PKGVERSION_NOREV:R}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.gnome.org/GNOME/libspelling
COMMENT=	Spellcheck library for GTK 4
LICENSE=	gnu-lgpl-v2.1

TOOL_DEPENDS+=	${PYPKGPREFIX}-gi-docgen-[0-9]*:../../devel/py-gi-docgen
TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection

TOOL_DEPENDS+=	vala>=0.56.19:../../lang/vala
MESON_BINARIES+=	vapigen
MESON_BINARY.vapigen=	${TOOLBASE}/bin/vapigen

USE_TOOLS+=	pkg-config

MESON_ARGS+=	-Dsysprof=false

PKG_OPTIONS_VAR= PKG_OPTIONS.libspelling
PKG_SUPPORTED_OPTIONS= tests
.include "../../mk/bsd.options.mk"
.if !empty(PKG_OPTIONS:Mtests)
MESON_ARGS+= -Dbuild-tests=true
.else
MESON_ARGS+= -Dbuild-tests=false
.endif

PKGCONFIG_OVERRIDE+=		output/meson-private/libspelling-1.pc
PKGCONFIG_OVERRIDE_STAGE=	post-configure

.include "../../lang/python/pyversion.mk"
BUILDLINK_DEPMETHOD.gobject-introspection= build
.include "../../devel/gobject-introspection/buildlink3.mk"
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
MESON_CROSS_VARS+= emberbsd_gir_dirs emberbsd_vapi_dirs
MESON_CROSS.emberbsd_gir_dirs= ['${CROSS_DESTDIR}${CROSS_LOCALBASE}/share/gir-1.0']
MESON_CROSS.emberbsd_vapi_dirs= ['${CROSS_DESTDIR}${CROSS_LOCALBASE}/share/vala/vapi']
.endif

.include "../../textproc/enchant2/buildlink3.mk"
.include "../../textproc/icu/buildlink3.mk"
.include "../../x11/gtk4/buildlink3.mk"
.include "../../x11/gtksourceview5/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
