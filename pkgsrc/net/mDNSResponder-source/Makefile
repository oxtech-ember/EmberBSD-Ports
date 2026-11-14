.include "../../net/mDNSResponder/Makefile.common"

PKGNAME=	mDNSResponder-source-${PKGVER}
PKGREVISION=	5
CATEGORIES=	net
HOMEPAGE=	https://developer.apple.com/bonjour/
COMMENT=	Prepared mDNSResponder source with the common Ports patchset
LICENSE=	apache-2.0 AND modified-bsd

DISTINFO_FILE=	${.CURDIR}/../../net/mDNSResponder/distinfo
PATCHDIR=	${.CURDIR}/../../net/mDNSResponder/patches
WRKSRC=		${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_PROJECT}-${PKGVER}
NO_ARCH=	yes
NO_BUILD=	yes
NO_CONFIGURE=	yes
USE_LANGUAGES=	# source only
USE_TOOLS+=	find sort
INSTALLATION_DIRS=	share/mDNSResponder-source

do-install:
	${CP} -R ${WRKSRC}/. ${DESTDIR}${PREFIX}/share/mDNSResponder-source/
	${FIND} ${DESTDIR}${PREFIX}/share/mDNSResponder-source -name '*.orig' -exec ${RM} {} +
	${INSTALL_DATA} ${.CURDIR}/README.md ${DESTDIR}${PREFIX}/share/mDNSResponder-source/README.EmberBSD.md

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/mDNSResponder-source \( -type f -o -type l \) -print | ${SORT};
CHECK_INTERPRETER_SKIP+= share/mDNSResponder-source/*
.include "../../mk/bsd.pkg.mk"
