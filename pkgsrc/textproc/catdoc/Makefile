# $NetBSD: Makefile,v 1.33 2023/03/13 10:18:47 wiz Exp $

.include "Makefile.common"

CONFIGURE_ARGS+=	--disable-wordview
CONFIGURE_ENV+=		man1dir=${PREFIX}/${PKGMANDIR}/man1
INSTALLATION_DIRS=	${PKGMANDIR}/man1

.include "../../mk/bsd.pkg.mk"

# The upstream top-level install rule does not propagate the cross
# environment into its sub-makes and stages nothing. Install each
# subdirectory directly with the wrapped toolchain.
do-install:
	cd ${WRKSRC}/src && ${SETENV} ${MAKE_ENV} gmake install
	cd ${WRKSRC}/charsets && ${SETENV} ${MAKE_ENV} gmake install
	cd ${WRKSRC}/doc && ${SETENV} ${MAKE_ENV} gmake install
