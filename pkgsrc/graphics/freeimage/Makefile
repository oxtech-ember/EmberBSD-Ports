# Origin: EmberBSD, current system-codec FreeImage provider.
.include "Makefile.common"

PKGNAME=	freeimage-3.19.25
PKGREVISION=	3
MAINTAINER=	pkgsrc-users@NetBSD.org
COMMENT=	Image decoding, conversion and encoding library (maintained fork)

CMAKE_CONFIGURE_ARGS+=	-DFREEIMAGE_USE_SYSTEM_LIBS=ON
CMAKE_CONFIGURE_ARGS+=	-DFREEIMAGE_STATIC=OFF
CMAKE_CONFIGURE_ARGS+=	-DFREEIMAGE_BUILD_STATIC=ON
CMAKE_CONFIGURE_ARGS+=	-DFREEIMAGE_LINUX_PACKAGE_LAYOUT=ON
CMAKE_CONFIGURE_ARGS+=	-DCPP_STANDARD=17
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTS=ON
TEST_TARGET=		test

# Keep all canonical codecs. Optional HEIF/JXL/JXR retain upstream Unix defaults.
.include "../../devel/zlib/buildlink3.mk"
BUILDLINK_API_DEPENDS.libraw+=	libraw>=0.22.2
.include "../../graphics/libraw/buildlink3.mk"
.include "../../graphics/libwebp/buildlink3.mk"
BUILDLINK_API_DEPENDS.openexr+=	openexr>=3.5.2
.include "../../graphics/openexr/buildlink3.mk"
.include "../../graphics/openjpeg/buildlink3.mk"
.include "../../graphics/png/buildlink3.mk"
.include "../../graphics/tiff/buildlink3.mk"
.include "../../math/imath/buildlink3.mk"
JPEG_ACCEPTED=		libjpeg-turbo
BUILDLINK_API_DEPENDS.libjpeg-turbo+=	libjpeg-turbo>=3.2.0
.include "../../mk/jpeg.buildlink3.mk"
.include "../../mk/bsd.prefs.mk"
PLIST_VARS+=		darwin elf
.if ${OPSYS} == "Darwin"
PLIST.darwin=		yes
.else
PLIST.elf=		yes
.endif

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
