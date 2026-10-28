# $NetBSD: Makefile,v 1.167 2026/09/02 19:02:49 wiz Exp $

.include "Makefile.common"

DISTNAME=	opencv-${OPENCV_VERSION}
PKGREVISION=	3

MAINTAINER=	anthony.mallet@laas.fr
COMMENT=	Library for computer vision problems

# cv2 is built by graphics/opencv-contrib, with every module.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_opencv_python3=OFF

PLIST_VARS+=	opencl

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} != "Darwin"
PLIST.opencl=	yes
.endif

.include "options.mk"

TEST_ENV+=	LD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/lib
# For Darwin
TEST_ENV+=	DYLD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/lib
TEST_TARGET=	test

post-install:
	${MV} ${DESTDIR}${PREFIX}/share/licenses/opencv5 ${DESTDIR}${PREFIX}/share/opencv5/licenses

.include "../../devel/protobuf/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../graphics/libavif/buildlink3.mk"
.include "../../graphics/libwebp/buildlink3.mk"
.include "../../graphics/openexr/buildlink3.mk"
BUILDLINK_API_DEPENDS.openjpeg+=	openjpeg>=2.3.1
.include "../../graphics/openjpeg/buildlink3.mk"
.include "../../graphics/png/buildlink3.mk"
.include "../../graphics/tiff/buildlink3.mk"
.include "../../mk/jpeg.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
