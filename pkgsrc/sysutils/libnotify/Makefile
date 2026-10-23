# $NetBSD: Makefile,v 1.96 2026/09/29 06:07:38 wiz Exp $
.include "../../mk/bsd.prefs.mk"

DISTNAME=	libnotify-0.8.9
CATEGORIES=	sysutils gnome
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/${PKGBASE}/${PKGVERSION_NOREV:R}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.gnome.org/GNOME/libnotify
COMMENT=	Desktop notification framework
LICENSE=	gnu-lgpl-v2.1

TOOL_DEPENDS+=	docbook-xsl-ns-[0-9]*:../../textproc/docbook-xsl-ns
PLIST_VARS+=	introspection
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection
.endif
TOOL_DEPENDS+=	libxslt-[0-9]*:../../textproc/libxslt

CONFLICTS+=	libnotify07-[0-9]*
SUPERSEDES+=	libnotify07-[0-9]*

USE_TOOLS+=	pkg-config

PKGCONFIG_OVERRIDE=		output/meson-private/libnotify.pc
PKGCONFIG_OVERRIDE_STAGE=	pre-install

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Cross consumers use the C API; target-side GIR output is unnecessary.
MESON_ARGS+=	-Dintrospection=disabled
MESON_BINARIES+=	glib-mkenums glib-genmarshal
MESON_BINARY.glib-mkenums=	${TOOLBASE}/bin/glib-mkenums
MESON_BINARY.glib-genmarshal=	${TOOLBASE}/bin/glib-genmarshal
.else
MESON_ARGS+=	-Dintrospection=enabled
PLIST.introspection=	yes
.endif

# Apply removals to post-wrapper transformed arguments.
BUILDLINK_TRANSFORM.SunOS+=	rm:-Wl,--version-script
BUILDLINK_TRANSFORM.SunOS+=	rm:-Wl,${WRKSRC}/libnotify/libnotify.map

PYTHON_FOR_BUILD_ONLY=	tool

.include "options.mk"

.include "../../graphics/gdk-pixbuf2/buildlink3.mk"
BUILDLINK_API_DEPENDS.glib2+=	glib2>=2.62.0
.include "../../devel/glib2/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
BUILDLINK_DEPMETHOD.gobject-introspection=	build
.include "../../devel/gobject-introspection/buildlink3.mk"
.endif
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
