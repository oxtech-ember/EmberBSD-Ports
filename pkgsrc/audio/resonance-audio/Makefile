# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted); Qt Multimedia core source list.
DISTNAME= resonance-audio-20220908
CATEGORIES= audio
MASTER_SITES= ${MASTER_SITE_GITHUB:=resonance-audio/}
GITHUB_PROJECT= resonance-audio
GITHUB_TAG= 4556a46afd4ffae092aa281bfd072eb0279d3a29
WRKSRC= ${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_TAG}
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/resonance-audio/resonance-audio/
COMMENT= Spatial audio rendering library
LICENSE= apache-2.0
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++14
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+= -DCMAKE_POSITION_INDEPENDENT_CODE=ON
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
PKGREVISION= 1
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif
PLIST_VARS+= darwin elf
.if ${OPSYS} == "Darwin"
PLIST.darwin= yes
.else
PLIST.elf= yes
.endif
INSTALLATION_DIRS+= share/licenses/resonance-audio
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/resonance-audio/LICENSE
	${INSTALL_DATA} ${WRKSRC}/third_party/SADIE_hrtf_database/LICENSE ${DESTDIR}${PREFIX}/share/licenses/resonance-audio/SADIE-LICENSE
	${INSTALL_DATA} ${WRKSRC}/third_party/SADIE_hrtf_database/WAV/Subject_002/SH/README ${DESTDIR}${PREFIX}/share/licenses/resonance-audio/SADIE-README
post-extract:
	${CP} ${FILESDIR}/CMakeLists.txt ${WRKSRC}/CMakeLists.txt
	${CP} ${FILESDIR}/resonance_audio-config.cmake.in ${WRKSRC}/resonance_audio-config.cmake.in
.include "../../devel/cmake/build.mk"
.include "../../math/eigen3/buildlink3.mk"
.include "../../audio/pffft/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
