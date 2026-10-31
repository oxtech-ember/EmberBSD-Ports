# $NetBSD$
# Origin: Apple cctools via the cctools-port project.

DISTNAME= cctools-port-1030.6.3
PKGNAME= cctools-codesign-allocate-1030.6.3
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=tpoechtrager/}
GITHUB_PROJECT= cctools-port
GITHUB_TAG= 904de2a71d4da6a9b30d2efaf912a10ddc7d9ddb
WRKSRC= ${WRKDIR}/cctools-port-${GITHUB_TAG}/cctools

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/tpoechtrager/cctools-port/
COMMENT= Mach-O code signature allocation tool
LICENSE= apple-public-source-license

GNU_CONFIGURE= yes
USE_LANGUAGES= c c++
USE_TOOLS+= gmake
USE_LIBTOOL= yes
CONFIGURE_ARGS+= --disable-shared --enable-static
# Only ld64 uses the Blocks runtime and libdispatch; it is not built here.
CONFIGURE_ARGS+= --disable-blocks-dispatch
# libLTO is optional, and the llvm-config found in PATH describes the build
# machine, not the target.
CONFIGURE_ARGS+= --disable-lto-support
INSTALLATION_DIRS= bin share/licenses/cctools-codesign-allocate

do-build:
	cd ${WRKSRC}/libstuff && ${SETENV} ${MAKE_ENV} ${MAKE_PROGRAM}
	cd ${WRKSRC}/libmacho && ${SETENV} ${MAKE_ENV} ${MAKE_PROGRAM}
	cd ${WRKSRC}/misc && ${SETENV} ${MAKE_ENV} ${MAKE_PROGRAM} codesign_allocate

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/misc/codesign_allocate ${DESTDIR}${PREFIX}/bin/codesign_allocate
	${INSTALL_DATA} ${WRKSRC}/APPLE_LICENSE ${DESTDIR}${PREFIX}/share/licenses/cctools-codesign-allocate/APPLE_LICENSE

.include "../../mk/bsd.pkg.mk"
