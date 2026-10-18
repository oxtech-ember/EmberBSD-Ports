# Origin: EmberBSD, current C++ wrapper using the common FreeImage C library.
.include "../../graphics/freeimage/Makefile.common"

PKGNAME=	freeimageplus-3.19.25
MAINTAINER=	pkgsrc-users@NetBSD.org
COMMENT=	C++ wrapper for the maintained FreeImage library
CMAKE_CONFIGURE_ARGS+=	-DFREEIMAGE_SOURCE_ROOT=${WRKSRC}
TEST_TARGET=		test

pre-configure:
	${CP} ${FILESDIR}/CMakeLists.txt ${WRKSRC}/CMakeLists.txt

.include "../../graphics/freeimage/buildlink3.mk"
.include "../../mk/bsd.prefs.mk"
PLIST_VARS+=		darwin elf
.if ${OPSYS} == "Darwin"
PLIST.darwin=		yes
.else
PLIST.elf=		yes
.endif

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
