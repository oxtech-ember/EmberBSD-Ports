# $NetBSD$
# Origin: KhronosGroup/EGL-Registry snapshot 8e56e86e65687697ef54114cdb1afabdfac756bf

EGL_REGISTRY_COMMIT=8e56e86e65687697ef54114cdb1afabdfac756bf
DISTNAME=EGL-Registry-${EGL_REGISTRY_COMMIT}
PKGNAME=egl-headers-20261106
CATEGORIES=graphics
MASTER_SITES=	${MASTER_SITE_GITHUB:=KhronosGroup/}
GITHUB_PROJECT=EGL-Registry
GITHUB_TAG=${EGL_REGISTRY_COMMIT}
WRKSRC=${WRKDIR}/EGL-Registry-${EGL_REGISTRY_COMMIT}

MAINTAINER=pkgsrc-users@NetBSD.org
HOMEPAGE=https://github.com/KhronosGroup/EGL-Registry
COMMENT=Shared EGL and Khronos platform headers
LICENSE=apache-2.0 AND modified-bsd

NO_CONFIGURE=yes
NO_BUILD=yes
USE_LANGUAGES=none

INSTALLATION_DIRS=include/EGL include/KHR

do-install:
	${INSTALL_DATA} ${WRKSRC}/api/EGL/eglplatform.h ${DESTDIR}${PREFIX}/include/EGL/eglplatform.h
	${INSTALL_DATA} ${WRKSRC}/api/KHR/khrplatform.h ${DESTDIR}${PREFIX}/include/KHR/khrplatform.h

.include "../../mk/bsd.pkg.mk"
