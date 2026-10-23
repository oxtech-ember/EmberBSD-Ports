# $NetBSD: Makefile,v 1.6 2026/09/02 19:01:45 wiz Exp $
# Origin: pkgsrc devel/swig4; EmberBSD (AI-assisted) current stable release.

DISTNAME=	swig-4.5.1
PKGNAME=	${DISTNAME:S/swig/swig4/}
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_SOURCEFORGE:=swig/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.swig.org/
COMMENT=	Simplified Wrapper and Interface Generator (version 4)
LICENSE=	gnu-gpl-v3

USE_LANGUAGES=		c c++
USE_TOOLS+=		gmake perl:build
GNU_CONFIGURE=		yes
GNU_CONFIGURE_STRICT=	no # has sub-configure
CONFIGURE_ARGS+=	--program-suffix=4.0
CONFIGURE_ARGS+=	--with-swiglibdir=${PREFIX}/share/swig/4.0

INSTALLATION_DIRS+=	share/licenses/swig4

BUILD_TARGET=	swig

post-install:
.for name in LICENSE LICENSE-GPL LICENSE-UNIVERSITIES COPYRIGHT
	${INSTALL_DATA} ${WRKSRC}/${name} \
	    ${DESTDIR}${PREFIX}/share/licenses/swig4/${name}
.endfor
	${INSTALL_DATA} ${WRKSRC}/CCache/COPYING \
	    ${DESTDIR}${PREFIX}/share/licenses/swig4/CCache-COPYING

BUILDLINK_API_DEPENDS.pcre2+=	pcre2>=10.49
.include "../../devel/pcre2/buildlink3.mk"
# The upstream CCache executable keeps its compressed-cache support.
BUILDLINK_API_DEPENDS.zlib+=	zlib>=1.3.2
.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
