# $NetBSD: Makefile,v 1.51 2023/11/12 13:20:47 wiz Exp $
# Origin: EmberBSD (AI-assisted); CLI with the matching common model provider.

.include "../../cad/ng-spice/Makefile.common"

PKGNAME=	ng-spice-${VERSION}
COMMENT=	Next generation circuit simulation program
DEPENDS+=	ng-spice-shared-${VERSION}nb${PKGREVISION}:../../cad/ng-spice-shared

CONFIGURE_ARGS+=	--with-ngshared=no --with-readline=yes --with-editline=no --without-x

post-configure: ngspice-readline-check
.PHONY: ngspice-readline-check
ngspice-readline-check:
	${RUN} ${GREP} '^\#define HAVE_GNUREADLINE ' ${WRKSRC}/src/include/ngspice/config.h > /dev/null

# The matching shared package owns these identical common model/data paths.
# Both interfaces are built completely. Only duplicate staged payloads are removed.
post-install:
	${RUN} test -n ${DESTDIR:Q}
	${RM} -r ${DESTDIR}${PREFIX}/lib/ngspice ${DESTDIR}${PREFIX}/share/ngspice

.include "../../devel/readline/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
