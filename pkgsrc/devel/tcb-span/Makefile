# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= tcb-span-20220615
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=tcbrindle/}
GITHUB_PROJECT= span
GITHUB_TAG= 836dc6a0efd9849cb194e88e4aa2387436bb079b
WRKSRC= ${WRKDIR}/span-${GITHUB_TAG}

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/tcbrindle/span
COMMENT= Single-header C++11 implementation of std::span
LICENSE= boost-license

NO_BUILD= yes
NO_ARCH= yes
USE_LANGUAGES= # header-only
INSTALLATION_DIRS= include/tcb share/licenses/${PKGBASE}

do-install:
	${INSTALL_DATA} ${WRKSRC}/include/tcb/span.hpp ${DESTDIR}${PREFIX}/include/tcb/span.hpp
	${INSTALL_DATA} ${WRKSRC}/LICENSE_1_0.txt ${DESTDIR}${PREFIX}/share/licenses/${PKGBASE}/LICENSE_1_0.txt

.include "../../mk/bsd.pkg.mk"
