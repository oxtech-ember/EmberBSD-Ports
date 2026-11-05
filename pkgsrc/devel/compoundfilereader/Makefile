# $NetBSD$
# Origin: Microsoft upstream plus the compatible KiCad 10.0.8 reader fork.
DISTNAME=	compoundfilereader-0.0.20250414
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=microsoft/}
GITHUB_TAG=	4ddb0602600833bc925d76c0f0382ba88c1c9f60
WRKSRC=		${WRKDIR}/compoundfilereader-${GITHUB_TAG}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/microsoft/compoundfilereader
COMMENT=	Header-only Microsoft Compound File reader
LICENSE=	mit AND apache-2.0

NO_BUILD=	yes
USE_LANGUAGES=	# none
INSTALLATION_DIRS+=	include lib/cmake/CompoundFileReader share/licenses/compoundfilereader

do-install:
	${INSTALL_DATA} ${WRKSRC}/src/include/compoundfilereader.h ${DESTDIR}${PREFIX}/include/compoundfilereader.h
	${INSTALL_DATA} ${WRKSRC}/src/include/utf.h ${DESTDIR}${PREFIX}/include/utf.h
	${INSTALL_DATA} ${FILESDIR}/CompoundFileReaderConfig.cmake ${DESTDIR}${PREFIX}/lib/cmake/CompoundFileReader/CompoundFileReaderConfig.cmake
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/compoundfilereader/LICENSE
	${INSTALL_DATA} ${PKGSRCDIR}/licenses/apache-2.0 ${DESTDIR}${PREFIX}/share/licenses/compoundfilereader/LICENSE.apache-2.0

.include "../../mk/bsd.pkg.mk"
