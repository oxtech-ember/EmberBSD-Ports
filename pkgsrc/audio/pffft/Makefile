# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= pffft-1.1.0
CATEGORIES= audio
MASTER_SITES= ${MASTER_SITE_GITHUB:=marton78/}
GITHUB_TAG= v${PKGVERSION_NOREV}
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/marton78/pffft/
COMMENT= SIMD-accelerated fast Fourier transform library
LICENSE= modified-bsd
USE_LANGUAGES= c c++
CMAKE_CONFIGURE_ARGS+= -DPFFFT_BUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+= -DPFFFT_BUILD_BENCHMARKS=OFF
CMAKE_CONFIGURE_ARGS+= -DPFFFT_BUILD_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+= -DCMAKE_POSITION_INDEPENDENT_CODE=ON
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON
PLIST_VARS+= darwin elf
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
PLIST.darwin= yes
.else
PLIST.elf= yes
.endif
INSTALLATION_DIRS+= share/licenses/pffft
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE.txt ${DESTDIR}${PREFIX}/share/licenses/pffft/LICENSE.txt
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
