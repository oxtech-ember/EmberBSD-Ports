# $NetBSD$
# Origin: EmberBSD contributors; maintained KiCad fork, preserving upstream licenses.
DISTNAME=	kicad-10.0.8
PKGNAME=	libcontext-20261029
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITLAB:=kicad/code/}
GITLAB_PROJECT=	kicad
GITLAB_RELEASE=	10.0.8
EXTRACT_SUFX=	.tar.bz2
EXTRACT_ELEMENTS=	${DISTNAME}/thirdparty/libcontext
WRKSRC=		${WRKDIR}/${DISTNAME}/thirdparty/libcontext
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.com/kicad/code/kicad/-/tree/10.0.8/thirdparty/libcontext
COMMENT=	Portable stackful context switching with KiCad maintained platforms
LICENSE=	boost-license
USE_LANGUAGES=	c++
post-extract:
	${CP} ${FILESDIR}/CMakeLists.txt ${WRKSRC}/CMakeLists.txt
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
