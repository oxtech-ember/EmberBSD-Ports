# $NetBSD$

.include "version.mk"

DISTNAME=	gvdb-${GVDB_VERSION}
PKGNAME=	gvdb-source-${GVDB_VERSION}
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=GNOME/}
GITHUB_PROJECT=	gvdb
GITHUB_TAG=	${GVDB_COMMIT}
WRKSRC=		${WRKDIR}/gvdb-${GITHUB_TAG}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.gnome.org/GNOME/gvdb
COMMENT=	GNOME GVariant database reader and builder sources
LICENSE=	gnu-lgpl-v2.1

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes"
PKGREVISION=	1	# Reissue the native package with public build metadata.
.endif

USE_LANGUAGES=	# none
NO_CONFIGURE=	yes
NO_BUILD=	yes
INSTALLATION_DIRS= share/gvdb-source share/gvdb-source/LICENSES \
	share/gvdb-source/gvdb share/gvdb-source/gvdb/tests

do-install:
	cd ${WRKSRC} && ${INSTALL_DATA} COPYING meson.build meson.options \
	    ${DESTDIR}${PREFIX}/share/gvdb-source
	${INSTALL_DATA} ${WRKSRC}/LICENSES/LGPL-2.1-or-later.txt \
	    ${DESTDIR}${PREFIX}/share/gvdb-source/LICENSES
	${INSTALL_DATA} ${WRKSRC}/gvdb/*.[ch] ${DESTDIR}${PREFIX}/share/gvdb-source/gvdb
	${INSTALL_DATA} ${WRKSRC}/gvdb/tests/*.c ${WRKSRC}/gvdb/tests/meson.build \
	    ${DESTDIR}${PREFIX}/share/gvdb-source/gvdb/tests

.include "../../mk/bsd.pkg.mk"
