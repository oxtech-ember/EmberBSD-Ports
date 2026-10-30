# $NetBSD: Makefile,v 1.38 2026/01/07 08:49:10 wiz Exp $

DISTNAME=		xmlstarlet-1.7.0
CATEGORIES=		textproc
MASTER_SITES=		https://github.com/xmlstarlet/xmlstarlet/releases/download/${PKGVERSION_NOREV}/

MAINTAINER=		pkgsrc-users@NetBSD.org
HOMEPAGE=		https://github.com/xmlstarlet/xmlstarlet
COMMENT=		Command line utilities for XML manipulation
LICENSE=		mit

USE_PKGLOCALEDIR=	yes
GNU_CONFIGURE=		yes
USE_TOOLS+=		pkg-config
CONFIGURE_ARGS+=	--with-libxml-prefix=${BUILDLINK_PREFIX.libxml2}
CONFIGURE_ARGS+=	--with-libxslt-prefix=${BUILDLINK_PREFIX.libxslt}
PTHREAD_OPTS+=		require

BUILDLINK_API_DEPENDS.libxml2+=	libxml2>=2.6.12
BUILDLINK_API_DEPENDS.libxslt+=	libxslt>=1.1.9

TEST_TARGET=	check

.include "../../textproc/libxml2/buildlink3.mk"
.include "../../textproc/libxslt/buildlink3.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
