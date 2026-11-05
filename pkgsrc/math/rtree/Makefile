# $NetBSD$
# Origin: KiCad 10.0.8 thirdparty/rtree subtree; GPLv3 KiCad-maintained API fork.
DISTNAME=	kicad-10.0.8
PKGNAME=	rtree-10.0.8
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITLAB:=kicad/code/}
GITLAB_PROJECT=	kicad
GITLAB_RELEASE=	10.0.8
EXTRACT_SUFX=	.tar.bz2
EXTRACT_ELEMENTS=	${DISTNAME}/thirdparty/rtree
WRKSRC=		${WRKDIR}/${DISTNAME}/thirdparty/rtree
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.com/kicad/code/kicad/-/tree/10.0.8/thirdparty/rtree
COMMENT=	KiCad-maintained C++ R-tree spatial index
LICENSE=	gnu-gpl-v3
USE_LANGUAGES=	c++
USE_CXX_FEATURES=	c++17
INSTALLATION_DIRS+=	share/licenses/rtree
post-extract:
	${MKDIR} ${WRKSRC}/cmake
	${CP} ${FILESDIR}/rtreeConfig.cmake.in ${WRKSRC}/cmake/rtreeConfig.cmake.in
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE.GPLv3 ${DESTDIR}${PREFIX}/share/licenses/rtree/LICENSE.GPLv3
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
