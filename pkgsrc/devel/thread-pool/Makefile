# $NetBSD$

DISTNAME=	thread-pool-5.1.0
PKGREVISION=	1
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=bshoshany/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/bshoshany/thread-pool
COMMENT=	Fast, lightweight C++17 header-only thread pool
LICENSE=	mit

NO_BUILD=	yes
USE_LANGUAGES=	# none

INSTALLATION_DIRS+=	include share/licenses/thread-pool lib/cmake/BS_thread_pool
do-install:
	${INSTALL_DATA} ${WRKSRC}/include/BS_thread_pool.hpp ${DESTDIR}${PREFIX}/include/BS_thread_pool.hpp
	${INSTALL_DATA} ${WRKSRC}/LICENSE.txt ${DESTDIR}${PREFIX}/share/licenses/thread-pool/LICENSE.txt
	${INSTALL_DATA} ${FILESDIR}/BS_thread_poolConfig.cmake ${DESTDIR}${PREFIX}/lib/cmake/BS_thread_pool/BS_thread_poolConfig.cmake

.include "../../mk/bsd.pkg.mk"
