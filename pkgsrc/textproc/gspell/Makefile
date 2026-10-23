# $NetBSD: Makefile,v 1.62 2026/09/30 09:10:50 adam Exp $

DISTNAME=	gspell-1.14.5
CATEGORIES=	textproc gnome
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/gspell/${PKGVERSION_NOREV:R}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	prlw1@cam.ac.uk
HOMEPAGE=	https://wiki.gnome.org/Projects/gspell
COMMENT=	Spell checking API for GTK+ applications
LICENSE=	gnu-lgpl-v2.1

TOOL_DEPENDS+=		glib2-introspection>=0:../../devel/glib2-introspection
# VAPI generation runs on the build host and uses its packaged VAPI data.
TOOL_DEPENDS+=		vala>=0.56.19:../../lang/vala
MESON_BINARIES+=		vapigen
MESON_BINARY.vapigen=	${TOOLBASE}/bin/vapigen-0.56

USE_LANGUAGES=		c
USE_PKGLOCALEDIR=	yes
USE_TOOLS+=		msgfmt pkg-config

MESON_ARGS+=	-Dgtk_doc=false
MESON_ARGS+=	-Dinstall_tests=false # fail on Darwin

PKGCONFIG_OVERRIDE+=		output/meson-private/gspell-1.pc
PKGCONFIG_OVERRIDE_STAGE=	post-configure

.include "../../mk/bsd.prefs.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Keep target GIR and VAPI. Share the existing native GI tools and target queries.
EMBERBSD_GI_MESON_OPTIONS=	no
.include "../../devel/gobject-introspection/cross.mk"
.endif

.include "../../devel/glib2/buildlink3.mk"
BUILDLINK_DEPMETHOD.gobject-introspection=	build
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../textproc/enchant2/buildlink3.mk"
.include "../../textproc/icu/buildlink3.mk"
.include "../../x11/gtk3/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
