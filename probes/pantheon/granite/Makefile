# elementary Granite library: widgets and utilities for Pantheon apps.
# Probe recipe for the Pantheon port (E25): distfile hashed on
# 2026-10-12; build not yet run. Current release line, GTK4-based.
DISTNAME=	granite-7.8.1
CATEGORIES=	x11
MASTER_SITES=	${MASTER_SITE_GITHUB:=elementary/}
GITHUB_RELEASE=	7.8.1

HOMEPAGE=	https://github.com/elementary/granite
COMMENT=	Elementary library of GTK4 widgets and utilities
LICENSE=	gnu-lgpl-v3

USE_TOOLS+=	pkg-config msgfmt

# Cross: valac/vapigen run on the host (homebrew vala 0.56.19, same line as
# the sysroot); the vapidir wrapper prefers the sysroot vapi set.
MESON_ARGS+=	-Dintrospection=false
MESON_ARGS+=	-Ddemo=false

.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/libgee/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../x11/gtk4/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
