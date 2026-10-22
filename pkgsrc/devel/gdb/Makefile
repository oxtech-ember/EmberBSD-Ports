# Origin: EmberBSD (AI-assisted), current native AArch64 debugger.
DISTNAME=	gdb-18.1
PKGREVISION=	1
CATEGORIES=	devel
MASTER_SITES=	https://sourceware.org/pub/gdb/releases/
EXTRACT_SUFX=	.tar.xz
PATCH_STRIP=	-p1
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://sourceware.org/gdb/
COMMENT=	GNU debugger with native EmberBSD AArch64 support
LICENSE=	gnu-gpl-v3
ONLY_FOR_PLATFORM=	NetBSD-*-aarch64

USE_LANGUAGES=	c gnu++17
USE_TOOLS+=	gmake makeinfo bison pkg-config
GNU_CONFIGURE=	yes
GNU_CONFIGURE_STRICT=	no
CONFIGURE_DIRS=	${WRKDIR}/build
CONFIGURE_SCRIPT=	${WRKSRC}/configure
BUILD_DIRS=	${CONFIGURE_DIRS}
BUILD_TARGET=	all-gdb
INSTALL_TARGET=	install-gdb
INFO_FILES=	yes
TEST_TARGET=	check-gdb
# The upstream ptrace probe uses pre-C23 non-prototype semantics.
CFLAGS+=	-std=gnu17
CONFIGURE_ARGS+=	--disable-binutils --disable-gas --disable-ld --disable-gprof
CONFIGURE_ARGS+=	--disable-sim --disable-gdbserver --disable-nls
CONFIGURE_ARGS+=	--without-python --without-guile --without-debuginfod
CONFIGURE_ARGS+=	--without-intel-pt --without-babeltrace --with-zstd
CONFIGURE_ARGS+=	--with-system-zlib --with-system-readline --with-curses
CONFIGURE_ARGS+=	--with-separate-debug-dir=/usr/libdata/debug --disable-rpath
CONFIGURE_ARGS+=	--with-gmp=${BUILDLINK_PREFIX.gmp}
CONFIGURE_ARGS+=	--with-mpfr=${BUILDLINK_PREFIX.mpfr}
CONFIGURE_ARGS+=	--with-libexpat-prefix=${BUILDLINK_PREFIX.expat}

.include "../../mk/bsd.prefs.mk"
post-extract:
	${MKDIR} ${WRKDIR}/build

# Sub-configure creates its bundled Libtool only during this target.
post-configure:
	cd ${WRKDIR}/build && ${SETENV} ${MAKE_ENV} ${GMAKE} configure-gdb
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
	${SH} ${FILESDIR}/libtool-sysroot.sh ${WRKDIR}/build/gdb/libtool ${CROSS_DESTDIR}
.endif

.include "../../devel/readline/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../archivers/xz/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../devel/gmp/buildlink3.mk"
.include "../../math/mpfr/buildlink3.mk"
.include "../../textproc/expat/buildlink3.mk"
.include "../../mk/curses.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
