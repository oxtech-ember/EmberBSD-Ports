# $NetBSD$
# Origin: EmberBSD contributors; maintained KiCad fork, preserving upstream licenses.
DISTNAME=	kicad-10.0.8
PKGNAME=	sundown-1.16.0.20261029
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITLAB:=kicad/code/}
GITLAB_PROJECT=	kicad
GITLAB_RELEASE=	10.0.8
EXTRACT_SUFX=	.tar.bz2
EXTRACT_ELEMENTS=	${DISTNAME}/thirdparty/markdown2html
WRKSRC=		${WRKDIR}/${DISTNAME}/thirdparty/markdown2html
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.com/kicad/code/kicad/-/tree/10.0.8/thirdparty/markdown2html
COMMENT=	KiCad-maintained Sundown Markdown parser and HTML renderer
LICENSE=	isc
USE_LANGUAGES=	c
post-extract:
	${CP} ${FILESDIR}/CMakeLists.txt ${WRKSRC}/CMakeLists.txt
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
