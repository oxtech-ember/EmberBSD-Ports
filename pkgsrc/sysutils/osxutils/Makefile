# $NetBSD$
# Origin: osxutils project.
DISTNAME= osxutils-1.9.0
PKGNAME= osxutils-setfflags-1.9.0
CATEGORIES= sysutils
MASTER_SITES= ${MASTER_SITE_GITHUB:=specious/}
GITHUB_PROJECT= osxutils
GITHUB_TAG= v${PKGVERSION_NOREV}
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/specious/osxutils/
COMMENT= Inspect and change native macOS Finder flags
LICENSE= gnu-gpl-v2
ONLY_FOR_PLATFORM= Darwin-*-*
USE_LANGUAGES= c
INSTALLATION_DIRS= bin ${PKGMANDIR}/man1 share/licenses/osxutils-setfflags

do-build:
	${CC} ${CPPFLAGS} ${CFLAGS} ${WRKSRC}/setfflags/setfflags.c ${LDFLAGS} -framework Carbon -o ${WRKSRC}/setfflags/setfflags

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/setfflags/setfflags ${DESTDIR}${PREFIX}/bin/setfflags
	${INSTALL_MAN} ${WRKSRC}/setfflags/setfflags.1 ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/setfflags.1
	${INSTALL_DATA} ${WRKSRC}/LICENSE.txt ${DESTDIR}${PREFIX}/share/licenses/osxutils-setfflags/LICENSE.txt

.include "../../mk/bsd.pkg.mk"
