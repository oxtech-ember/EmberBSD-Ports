# $NetBSD$

DISTNAME=	gtk4-layer-shell-1.3.0
CATEGORIES=	wm
MASTER_SITES=	${MASTER_SITE_GITHUB:=wmww/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/wmww/gtk4-layer-shell
COMMENT=	Wayland layer-shell protocol bindings for GTK4
LICENSE=	mit

USE_TOOLS+=	pkg-config

MESON_ARGS+=	-Dexamples=false
MESON_ARGS+=	-Ddocs=false
MESON_ARGS+=	-Dtests=false
MESON_ARGS+=	-Dsmoke-tests=false
MESON_ARGS+=	-Dintrospection=false
MESON_ARGS+=	-Dvapi=false

.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../x11/gtk4/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
