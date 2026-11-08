# $NetBSD$

DISTNAME=	libphonenumber-8.13.55
CATEGORIES=	comms
MASTER_SITES=	https://codeload.github.com/google/libphonenumber/tar.gz/refs/tags/v${PKGVERSION_NOREV}/
DISTFILES=	${DISTNAME}${EXTRACT_SUFX}
EXTRACT_SUFX=	.tar.gz

HOMEPAGE=	https://github.com/google/libphonenumber
COMMENT=	Google phone number parsing and formatting library
LICENSE=	apache-2.0

WRKSRC=		${WRKDIR}/${DISTNAME}/cpp

.include "../../devel/cmake/build.mk"

USE_LANGUAGES=	c c++
USE_CXX_FEATURES+=	c++17
USE_TOOLS+=	pkg-config

# Use the metadata shipped in the source tree. The host protoc generates
# the C++ protobuf sources. The geocoder and tests are not built.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_GEOCODER:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_STATIC_LIB:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DREGENERATE_METADATA:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DUSE_BOOST:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DUSE_STDMUTEX:BOOL=ON
CMAKE_CONFIGURE_ARGS+=	-DUSE_RE2:BOOL=OFF
# The sysroot protoc is a NetBSD binary. The metadata compiler must run here.
CMAKE_CONFIGURE_ARGS+=	-DPROTOC_BIN:FILEPATH=/Volumes/DATA/EmberBSD/sdk-native/llvm/bin/protoc

.include "../../devel/abseil/buildlink3.mk"
.include "../../devel/protobuf/buildlink3.mk"
.include "../../textproc/icu/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
