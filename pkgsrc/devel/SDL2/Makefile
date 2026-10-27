# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). SDL2 programs run on SDL3, the one SDL in the export.
DISTNAME=	sdl2-compat-2.32.74
PKGNAME=	${DISTNAME:S/sdl2-compat/SDL2/}
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=libsdl-org/}
GITHUB_PROJECT=	sdl2-compat
GITHUB_RELEASE=	release-${PKGVERSION_NOREV}

HOMEPAGE=	https://www.libsdl.org/
COMMENT=	SDL2 API and ABI implemented on top of SDL3
LICENSE=	zlib

USE_LANGUAGES=	c

# libSDL2 loads libSDL3.so.0 at run time through its ${PREFIX}/lib run path.
CMAKE_CONFIGURE_ARGS+=	-DSDL2COMPAT_TESTS=OFF

.include "../../devel/cmake/build.mk"
.include "../../devel/SDL3/buildlink3.mk"
.if ${PKG_BUILD_OPTIONS.SDL3:Mx11}
.  include "../../x11/libX11/buildlink3.mk"
.else
CMAKE_CONFIGURE_ARGS+=	-DSDL2COMPAT_X11=OFF
.endif
.include "../../mk/dlopen.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
