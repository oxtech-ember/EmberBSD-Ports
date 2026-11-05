# $NetBSD$
DISTNAME= GSL-5.0.1
PKGNAME= microsoft-gsl-5.0.1
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=microsoft/}
GITHUB_PROJECT= GSL
GITHUB_TAG= v${PKGVERSION_NOREV}
DISTFILES= GSL-5.0.1.tar.gz
SITES.GSL-5.0.1.tar.gz= -https://github.com/microsoft/GSL/archive/refs/tags/v5.0.1.tar.gz
HOMEPAGE= https://github.com/microsoft/GSL/
COMMENT= Microsoft C++ Core Guidelines Support Library
LICENSE= mit
USE_LANGUAGES= c++
CMAKE_CONFIGURE_ARGS+= -DGSL_TEST=OFF -DGSL_INSTALL=ON
INSTALLATION_DIRS+= share/licenses/microsoft-gsl
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/microsoft-gsl/LICENSE
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
