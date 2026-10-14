# Shared policy, not a separate build or dependency manager.
USE_LANGUAGES=		c c++
USE_CC_FEATURES=		c11
USE_CXX_FEATURES=	c++17
CMAKE_REQD+=		3.18

CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/../cpu.cmake

.include "../../mk/bsd.prefs.mk"
.if ${MACHINE_ARCH} == "aarch64"
CMAKE_CONFIGURE_ARGS+=	-DGGML_CPU_ARM_ARCH=armv8-a
.endif

INSTALLATION_DIRS+=	bin share/licenses/${PKGBASE} share/doc/${PKGBASE}

# Install selected executables only. Each statically includes its own GGML;
# no competing libggml, header, or CMake package is installed globally.
do-install:
.for program in ${AI_PROGRAMS}
	${INSTALL_PROGRAM} ${WRKSRC}/${CMAKE_BUILD_DIR}/bin/${program} ${DESTDIR}${PREFIX}/bin/
.endfor
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/${PKGBASE}/LICENSE
	${INSTALL_DATA} ${FILESDIR}/THIRD-PARTY-NOTICES ${DESTDIR}${PREFIX}/share/licenses/${PKGBASE}/THIRD-PARTY-NOTICES
	${INSTALL_DATA} ${FILESDIR}/SOURCE ${DESTDIR}${PREFIX}/share/doc/${PKGBASE}/SOURCE
.for notice in ${AI_NOTICES}
	${INSTALL_DATA} ${WRKSRC}/${notice} ${DESTDIR}${PREFIX}/share/licenses/${PKGBASE}/${notice:S,/,_,g}
.endfor

.include "../../devel/cmake/build.mk"
.include "../../mk/pthread.buildlink3.mk"
