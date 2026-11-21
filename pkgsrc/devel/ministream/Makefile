# $NetBSD$

DISTNAME=	ministream-0.99.1
CATEGORIES=	devel gnome
MASTER_SITES=	https://gitlab.gnome.org/GNOME/ministream/-/archive/${PKGVERSION_NOREV}/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.gnome.org/GNOME/ministream/
COMMENT=	GLib parser for application AppStream metadata
LICENSE=	gnu-lgpl-v2.1

# The upstream fixtures are compiled with the build-machine gresource tool.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
TOOL_DEPENDS+=	glib2-[0-9]*:../../devel/glib2
.endif

USE_TOOLS+=	pkg-config
MESON_ARGS+=	-Das-compare=disabled
MESON_ARGS+=	-Dintrospection=disabled

.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
