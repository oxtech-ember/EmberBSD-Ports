# $NetBSD: Makefile,v 1.1 2023/06/06 09:56:08 bouyer Exp $
# Origin: EmberBSD (AI-assisted); installed C API and common XSPICE modules.

.include "../../cad/ng-spice/Makefile.common"

PKGNAME=	ng-spice-shared-${VERSION}
COMMENT=	Next generation circuit simulation program (shared libraries)
CONFIGURE_ARGS+=	--with-ngshared=yes

INSTALLATION_DIRS+=	share/licenses/ngspice
post-install:
	${INSTALL_DATA} ${WRKSRC}/COPYING ${DESTDIR}${PREFIX}/share/licenses/ngspice/COPYING

.include "../../mk/bsd.pkg.mk"
