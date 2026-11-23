# $NetBSD: Makefile,v 1.3 2022/12/17 14:25:20 he Exp $

DISTNAME=	${GITHUB_PROJECT}-${PKGVERSION_NOREV}
PKGNAME=	${GITHUB_PROJECT}-2.1.0
PKGREVISION=	1
CATEGORIES=	net
MASTER_SITES=	${MASTER_SITE_GITHUB:=nanomsg/}
GITHUB_PROJECT=	nng
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://nng.nanomsg.org/
COMMENT=	Light-weight brokerless messaging
LICENSE=	mit

USE_LANGUAGES=	c99
CMAKE_CONFIGURE_ARGS+=	-DNNG_TOOLS:BOOL=ON

.include "options.mk"

INSTALLATION_DIRS+= share/licenses/nng

post-install:
.if !empty(PKG_OPTIONS:Mdoc)
	${TOOL_PYTHONBIN} ${FILESDIR}/install-manual.py ${WRKSRC:Q} \
	    ${DESTDIR:Q}${PREFIX:Q}/${PKGMANDIR} ${TOOLBASE:Q}/bin/lowdown
	cd ${WRKDIR}/nng-${NNG_DOCS_REV}/ref/v2.1 && \
	    ${PAX} -rw -pp * ${DESTDIR}${PREFIX}/share/doc/nng
.endif
	${INSTALL_DATA} ${WRKSRC}/LICENSE.txt \
	    ${DESTDIR}${PREFIX}/share/licenses/nng/LICENSE.txt

.include "../../devel/cmake/build.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"
