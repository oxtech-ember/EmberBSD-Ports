# $NetBSD: Makefile,v 1.41 2026/09/05 19:10:04 bsiegert Exp $

DISTNAME=	esbuild-0.28.2
GITHUB_TAG=	v${PKGVERSION_NOREV}
PKGREVISION=	5
CATEGORIES=	www
MASTER_SITES=	${MASTER_SITE_GITHUB:=evanw/}
DISTFILES=	${DEFAULT_DISTFILES} ${DISTNAME}.tgz
SITES.${DISTNAME}.tgz=	https://registry.npmjs.org/esbuild/-/
EXTRACT_DIR.${DISTNAME}.tgz=	${WRKSRC}/npm
EXTRACT_ONLY=	${DEFAULT_DISTFILES} ${DISTNAME}.tgz

MAINTAINER=	bsiegert@NetBSD.org
HOMEPAGE=	https://esbuild.github.io/
COMMENT=	Fast JavaScript bundler and minifier
LICENSE=	mit

GO_BUILD_PATTERN=	./cmd/...
INSTALLATION_DIRS+=	lib/node_modules/esbuild/lib lib/node_modules/esbuild/bin

do-install:
	${INSTALL_PROGRAM} ${WRKDIR}/.gopath/${GOPATH_BIN}/esbuild ${DESTDIR}${PREFIX}/bin/
	${INSTALL_DATA} ${WRKSRC}/npm/package/lib/main.js ${WRKSRC}/npm/package/lib/main.d.ts ${DESTDIR}${PREFIX}/lib/node_modules/esbuild/lib/
	${INSTALL_DATA} ${WRKSRC}/npm/package/package.json ${WRKSRC}/npm/package/LICENSE.md ${WRKSRC}/npm/package/README.md ${DESTDIR}${PREFIX}/lib/node_modules/esbuild/
	${LN} -s ../../../../bin/esbuild ${DESTDIR}${PREFIX}/lib/node_modules/esbuild/bin/esbuild

.include "go-modules.mk"

.include "../../lang/go/go-module.mk"
.include "../../mk/bsd.pkg.mk"
