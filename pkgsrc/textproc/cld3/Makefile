# $NetBSD$
DISTNAME= cld3-3.0.13
CATEGORIES= textproc
MASTER_SITES= ${MASTER_SITE_GITHUB:=google/}
GITHUB_TAG= ${PKGVERSION_NOREV}
DISTFILES= cld3-3.0.13.tar.gz
SITES.cld3-3.0.13.tar.gz= -https://github.com/google/cld3/archive/refs/tags/3.0.13.tar.gz
HOMEPAGE= https://github.com/google/cld3/
COMMENT= Compact language detector version 3
LICENSE= apache-2.0
USE_LANGUAGES= c c++
TOOL_DEPENDS+= protobuf>=36.2:../../devel/protobuf
CMAKE_CONFIGURE_ARGS+= -DCMAKE_POLICY_VERSION_MINIMUM=3.5
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON -DCLD3_BUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+= -DPROTOBUF_PROTOC_EXECUTABLE=${TOOLBASE}/bin/protoc
INSTALLATION_DIRS+= share/licenses/cld3
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/cld3/LICENSE
.include "../../devel/protobuf/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
