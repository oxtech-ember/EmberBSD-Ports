# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= LIEF-1.0.0
PKGNAME= lief-1.0.0
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=lief-project/}
GITHUB_PROJECT= LIEF
GITHUB_TAG= 1.0.0

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://lief.re/
COMMENT= Library for parsing and modifying executable formats
LICENSE= apache-2.0

USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++17
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+= -DLIEF_USE_CCACHE=OFF
CMAKE_CONFIGURE_ARGS+= -DFETCHCONTENT_FULLY_DISCONNECTED=ON
CMAKE_CONFIGURE_ARGS+= -DLIEF_OPT_MBEDTLS_EXTERNAL=ON
CMAKE_CONFIGURE_ARGS+= -DLIEF_EXTERNAL_SPDLOG=ON
CMAKE_CONFIGURE_ARGS+= -DLIEF_OPT_FROZEN_EXTERNAL=ON
CMAKE_CONFIGURE_ARGS+= -DLIEF_OPT_NLOHMANN_JSON_EXTERNAL=ON
CMAKE_CONFIGURE_ARGS+= -DLIEF_OPT_EXTERNAL_EXPECTED=ON
CMAKE_CONFIGURE_ARGS+= -DLIEF_OPT_UTFCPP_EXTERNAL=ON
CMAKE_CONFIGURE_ARGS+= -DLIEF_OPT_EXTERNAL_SPAN=ON
CMAKE_CONFIGURE_ARGS+= -DLIEF_EXTERNAL_SPAN_DIR=${BUILDLINK_PREFIX.tcb-span}/include
INSTALLATION_DIRS= share/licenses/${PKGBASE}
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX} && ${FIND} include/LIEF lib/cmake/LIEF \
    lib/pkgconfig/LIEF.pc lib/libLIEF.* share/LIEF share/licenses/lief \
    \( -type f -o -type l \) -print | ${SORT};

post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/${PKGBASE}/LICENSE

.include "../../devel/cmake/build.mk"
.include "../../security/mbedtls4/buildlink3.mk"
.include "../../devel/spdlog/buildlink3.mk"
.include "../../devel/frozen/buildlink3.mk"
.include "../../textproc/nlohmann-json/buildlink3.mk"
.include "../../devel/tl-expected/buildlink3.mk"
.include "../../textproc/utf8-cpp/buildlink3.mk"
.include "../../devel/tcb-span/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
