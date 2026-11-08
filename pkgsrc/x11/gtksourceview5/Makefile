# $NetBSD: Makefile,v 1.20 2026/09/02 19:05:10 wiz Exp $

DISTNAME=	gtksourceview-5.22.0
PKGNAME=	${DISTNAME:S/gtksourceview/gtksourceview5/}
CATEGORIES=	x11 gnome
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/gtksourceview/${PKGVERSION_NOREV:R}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	prlw1@cam.ac.uk
HOMEPAGE=	https://wiki.gnome.org/Projects/GtkSourceView
COMMENT=	Text widget that extends GTK4's GtkTextView widget (v5)
LICENSE=	gnu-lgpl-v2.1

TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection

TOOL_DEPENDS+=	vala>=0.56.19:../../lang/vala
MESON_BINARIES+=	vapigen
MESON_BINARY.vapigen=	${TOOLBASE}/bin/vapigen

MESON_ARGS+=	-Dintrospection=enabled

USE_TOOLS+=		msgfmt pkg-config itstool

PKG_OPTIONS_VAR= PKG_OPTIONS.gtksourceview5
PKG_SUPPORTED_OPTIONS= tests
.include "../../mk/bsd.options.mk"
.if !empty(PKG_OPTIONS:Mtests)
MESON_ARGS+= -Dbuild-tests=true
MESON_ARGS+= -Dbuild-testsuite=true
.else
MESON_ARGS+= -Dbuild-tests=false
MESON_ARGS+= -Dbuild-testsuite=false
.endif

PKGCONFIG_OVERRIDE+=	output/meson-private/gtksourceview-5.pc
PKGCONFIG_OVERRIDE_STAGE=	post-configure

MAKE_ENV+=	LD_LIBRARY_PATH=${WRKSRC}/output/gtksourceview

PYTHON_FOR_BUILD_ONLY=	tool

BUILDLINK_API_DEPENDS.glib2+=	glib2>=2.48
.include "../../devel/glib2/buildlink3.mk"
BUILDLINK_API_DEPENDS.gobject-introspection+=	gobject-introspection>=1.42.0
BUILDLINK_DEPMETHOD.gobject-introspection= build
.include "../../devel/gobject-introspection/buildlink3.mk"
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
MESON_CROSS_VARS+= emberbsd_gir_dirs emberbsd_vapi_dirs
MESON_CROSS.emberbsd_gir_dirs= ['${CROSS_DESTDIR}${CROSS_LOCALBASE}/share/gir-1.0']
MESON_CROSS.emberbsd_vapi_dirs= ['${CROSS_DESTDIR}${CROSS_LOCALBASE}/share/vala/vapi']
.endif
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"

.include "../../textproc/libxml2/buildlink3.mk"
.include "../../converters/fribidi/buildlink3.mk"
.include "../../devel/pcre2/buildlink3.mk"
.include "../../x11/gtk4/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
