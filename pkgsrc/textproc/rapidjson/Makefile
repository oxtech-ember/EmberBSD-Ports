# $NetBSD: Makefile,v 1.14 2025/12/21 09:00:30 markd Exp $
# Origin: EmberBSD (AI-assisted), installed GoogleTest and GCC16 checks.

DISTNAME=	rapidjson-1.1.0.20250205
PKGREVISION=	2
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=Tencent/}
GITHUB_TAG=	24b5e7a8b27f42fa16b96fc70aade9106cf7102f

MAINTAINER=	minskim@NetBSD.org
HOMEPAGE=	https://rapidjson.org/
COMMENT=	Fast JSON parser/generator with SAX/DOM style API
LICENSE=	modified-bsd

USE_LANGUAGES=		c++
USE_CXX_FEATURES=	c++17
# The unit tests and examples are target programs that a cross build cannot
# run and the package does not install. Their CMake subdirectories also
# include CTest, whose host query runs the build host's sw_vers and ps.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CMAKE_CONFIGURE_ARGS+=		-DRAPIDJSON_BUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=		-DRAPIDJSON_BUILD_EXAMPLES=OFF
.else
TEST_TARGET=		test
CMAKE_CONFIGURE_ARGS+=		-DRAPIDJSON_BUILD_TESTS=ON
CMAKE_CONFIGURE_ARGS+=		-DRAPIDJSON_USE_SYSTEM_GTEST=ON
.endif
CMAKE_CONFIGURE_ARGS+=		-DRAPIDJSON_BUILD_CXX11=OFF
CMAKE_CONFIGURE_ARGS+=		-DRAPIDJSON_BUILD_CXX17=ON
CMAKE_CONFIGURE_ARGS+=		-DCMAKE_CXX_STANDARD=17
# Keep the canonical package's documentation scope and portable binaries.
CMAKE_CONFIGURE_ARGS+=		-DCMAKE_DISABLE_FIND_PACKAGE_Doxygen=ON
CMAKE_CONFIGURE_ARGS+=		-DRAPIDJSON_ENABLE_INSTRUMENTATION_OPT=OFF
CMAKE_CONFIGURE_ARGS+=		-DCMAKE_EXPORT_COMPILE_COMMANDS=ON
# Let CMake derive the imported include prefix from its installed config file.
CMAKE_CONFIGURE_ARGS+=		-DCMAKE_INSTALL_DIR:STRING=lib/cmake/RapidJSON

PKGCONFIG_OVERRIDE+=	RapidJSON.pc.in

post-install:
	rm -f ${DESTDIR}${PREFIX}/share/doc/RapidJSON/examples/CMakeLists.txt.orig \
	    ${DESTDIR}${PREFIX}/share/doc/RapidJSON/examples/jsonx/jsonx.cpp.orig \
	    ${DESTDIR}${PREFIX}/share/doc/RapidJSON/examples/tutorial/tutorial.cpp.orig \
	    ${DESTDIR}${PREFIX}/include/rapidjson/writer.h.orig \
	    ${DESTDIR}${PREFIX}/include/rapidjson/prettywriter.h.orig \
	    ${DESTDIR}${PREFIX}/include/rapidjson/allocators.h.orig \
	    ${DESTDIR}${PREFIX}/include/rapidjson/pointer.h.orig

.include "../../devel/cmake/build.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
BUILDLINK_DEPMETHOD.googletest=	build
BUILDLINK_API_DEPENDS.googletest+=	googletest>=1.18.0
.include "../../devel/googletest/buildlink3.mk"
.endif
.include "../../mk/bsd.pkg.mk"
