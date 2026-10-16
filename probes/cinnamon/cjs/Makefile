# cjs: Cinnamon's JavaScript bindings (gjs fork on SpiderMonkey 140).
# Cinnamon probe; pinned to the mint27 branch line that carries the
# Wayland-complete Cinnamon 6.8 development state.
DISTNAME=	84e7840ce148b75f9d38b57d82cdc9a47dd3a7eb
PKGNAME=	cjs-140.1
CATEGORIES=	lang
MASTER_SITES=	https://github.com/linuxmint/cjs/archive/
WRKSRC=		${WRKDIR}/cjs-${DISTNAME}

HOMEPAGE=	https://github.com/linuxmint/cjs
COMMENT=	JavaScript bindings for Cinnamon (SpiderMonkey 140)
LICENSE=	mit AND gnu-lgpl-v2

USE_TOOLS+=	pkg-config
USE_LANGUAGES=	c c++

# meson project defaults: cpp_std=c++17, RTTI and exceptions off,
# matching the SpiderMonkey build configuration.
MESON_ARGS+=	-Dprofiler=disabled
MESON_ARGS+=	-Dinstalled_tests=false

# No GTK is linked into cjs on this profile; the shell loads GTK
# typelibs at runtime instead. cairo stays: the shell uses the
# cairo GI module.

.include "../../devel/glib2/buildlink3.mk"
.include "../../graphics/cairo/buildlink3.mk"
.include "../../devel/libffi/buildlink3.mk"
.include "../../lang/mozjs140/buildlink3.mk"
.include "../../mk/readline.buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
