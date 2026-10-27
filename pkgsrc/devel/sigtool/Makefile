# $NetBSD$
# Origin: nix-community/sigtool.

DISTNAME= sigtool-0.2.2
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=nix-community/}
GITHUB_TAG= v${PKGVERSION_NOREV}

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/nix-community/sigtool/
COMMENT= Ad-hoc signatures and entitlements for Mach-O files
LICENSE= mit

USE_LANGUAGES= c c++
USE_TOOLS+= pkg-config
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=OFF
INSTALLATION_DIRS+= share/licenses/sigtool

post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/sigtool/LICENSE

DEPENDS+= cctools-codesign-allocate>=1030.6.3:../../devel/cctools

.include "../../devel/cmake/build.mk"
.include "../../devel/CLI11/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.include "../../textproc/libplist/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
