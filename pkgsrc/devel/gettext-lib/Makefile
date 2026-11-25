# $NetBSD: Makefile,v 1.63 2026/07/23 20:10:39 tnn Exp $

.include "../../devel/gettext/Makefile.common"

PKGNAME=	${DISTNAME:S/-/-lib-/}
PKGREVISION=	2
COMMENT=	Internationalized Message Handling Library (libintl)

.if ${OPSYS} == "Darwin"
PKGREVISION=	3	# Build a relocatable native libintl.
CONFIGURE_ARGS+=	--enable-relocatable
BUILD_MAKE_FLAGS+=	localedir=/usr/pkg/share/locale
SUBST_CLASSES+=	darwin-libdir
SUBST_STAGE.darwin-libdir=	pre-configure
SUBST_FILES.darwin-libdir=	gettext-runtime/intl/Makefile.in
SUBST_SED.darwin-libdir=	-e 's|-DLIBDIR=\\"[$$][(]libdir[)]\\"|-DLIBDIR=\\"/usr/pkg/lib\\"|'
.endif

USE_LANGUAGES=		c
CONFIGURE_ARGS+=	--with-included-gettext
CONFIGURE_ARGS+=	--with-included-libintl
CONFIGURE_ARGS+=	--disable-csharp
CONFIGURE_ARGS+=	--disable-c++
CONFIGURE_ENV+=		PKGLOCALEDIR=${PKGLOCALEDIR}
MAKE_ENV+=		PKGLOCALEDIR=${PKGLOCALEDIR}
GNU_CONFIGURE_STRICT=	no # because of gettext-tools/examples

CFLAGS+=		${CFLAGS.${ICONV_TYPE}-iconv}
CFLAGS.gnu-iconv+=	-DHAVE_GNU_ICONV

INSTALL_MAKE_FLAGS=	${MAKE_FLAGS} localedir=${EGDIR}
INSTALL_MAKE_FLAGS+=	includedir=${PREFIX}/include/gettext

# The intl make dependencies also require gettext-runtime/config.h.
CONFIGURE_DIRS=		gettext-runtime
BUILD_DIRS=		gettext-runtime/intl

.include "../../converters/libiconv/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && \
    (${MACHINE_ARCH} == "aarch64" || ${MACHINE_ARCH} == "x86_64")
PKGREVISION=	3	# Record the base libc SONAME.
.endif

.include "../../mk/bsd.pkg.mk"
