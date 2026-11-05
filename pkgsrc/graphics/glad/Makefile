# $NetBSD$
# Origin: Dav1dde/glad v2.0.8; generator uses its packaged Khronos XML.
DISTNAME=	glad-2.0.8
CATEGORIES=	graphics
MASTER_SITES=	${MASTER_SITE_GITHUB:=Dav1dde/}
GITHUB_PROJECT=	glad
GITHUB_TAG=	v${PKGVERSION_NOREV}
WRKSRC=		${WRKDIR}/glad-${PKGVERSION_NOREV}
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/Dav1dde/glad
COMMENT=	OpenGL, EGL, GLX and WGL loader library and generator
LICENSE=	mit AND apache-2.0 AND cc0-1.0-universal
USE_LANGUAGES=	c

TOOL_DEPENDS+=		${PYPKGPREFIX}-jinja2-[0-9]*:../../textproc/py-jinja2
PYTHON_FOR_BUILD_ONLY=	tool

post-extract:
	${MKDIR} ${WRKSRC}/files
	${CP} ${FILESDIR}/gladConfig.cmake.in ${WRKSRC}/files/

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_INCLUDEDIR=include
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DPython_EXECUTABLE:FILEPATH=${TOOL_PYTHONBIN}

INSTALLATION_DIRS+=	share/licenses/glad
BUILDLINK_DEPMETHOD.libX11?=	build
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/glad/LICENSE

.include "../../lang/python/batteries-included.mk"
.include "../../lang/python/tool.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/xorgproto/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
