# $NetBSD: Makefile,v 1.3.2.1 2026/10/21 00:58:19 maya Exp $

#
# We can't omit PKGNAME here to handle PKG_OPTIONS.
#
PKGNAME=		${PHP_PKG_PREFIX}-${PHP_VERSION}
CATEGORIES=		lang

COMMENT=		PHP Hypertext Preprocessor version 8.6
LICENSE=		modified-bsd

TEST_TARGET=		test

USE_TOOLS+=		autoconf gmake lex
LIBTOOL_OVERRIDE=	# empty

PHP_VERSIONS_ACCEPTED=	86

.include "Makefile.php"

CGIDIR=			${PREFIX}/libexec/cgi-bin

CONFIGURE_ENV+=		lt_cv_path_SED=${SED:Q}
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The opcache JIT runs minilua, built with BUILD_CC, on the build machine.
# configure's default "gcc" is the target compiler wrapper in a cross build.
.  if defined(EMBERBSD_CROSS_BUILD_CC)
CONFIGURE_ENV+=		BUILD_CC=${EMBERBSD_CROSS_BUILD_CC:Q}
.  else
CONFIGURE_ENV+=		BUILD_CC=${NATIVE_CC:Q}
.  endif
# ext/phar runs PHP to make phar.php and phar.phar and prefers the
# sapi/cli/php it has just linked, a target executable in a cross build.
# Run the native php of the same version in TOOLBASE instead.
TOOL_DEPENDS+=		${PHP_PKG_PREFIX}-${PHP_VERSION}{,nb[0-9]*}:../../lang/php86
MAKE_FLAGS+=		PHP_EXECUTABLE=${TOOLBASE}/bin/php${PHP_VER}
MAKE_FLAGS+=		PHP_PHARCMD_EXECUTABLE=${TOOLBASE}/bin/php${PHP_VER}
.endif
MAKE_ENV+=		INSTALL_ROOT=${DESTDIR}

CONF_FILES=		${PHP_EGDIR}/php.ini-production ${PKG_SYSCONFDIR}/php.ini
PLIST_SUBST+=		PHPEXTDIR="${PHP_EXTENSION_DIR}"

# taken from devel/pkgconf/Makefile
PKGCONFIG_PATHS=	${PREFIX}/lib/pkgconfig
PKGCONFIG_PATHS+=	${PREFIX}/share/pkgconfig
PKGCONFIG_PATHS+=	/usr/lib/pkgconfig

# At this point, PREFIX is not set yet.
.if ${LOCALBASE} != ${X11BASE}
PKGCONFIG_PATHS+=	${X11BASE}/lib/pkgconfig
.endif

PHP_PKGCONFIG_PATH=	${PKGCONFIG_PATHS:ts:}
SUBST_FILES.path+=	${WRKDIR}/${PHP_PKGSRC_README:T}

REPLACE_PHP=		ext/phar/phar/phar.php run-tests.php

INSTALLATION_DIRS+=	${CGIDIR} ${PHP_EXTENSION_DIR} ${PHP_EGDIR} \
			${PHP_SHAREDIR}

PHP_PKGSRC_README=	../../lang/php/files/README.pkgsrc

# Make sure modules can link correctly
.if ${OPSYS} == "Darwin"
PKGREVISION=		1
CPPFLAGS+=		-DPHP_DARWIN_PACKAGE_LAYOUT
INSTALL_UNSTRIPPED=	yes
.endif

# Darwin < 9 (Mac OS X < 10.5 "Leopard") doesn't have gethostuuid(2)
# and lacks the zone memory allocator
.if !empty(MACHINE_PLATFORM:MDarwin-[0-8].*-*)
CFLAGS+=	-DSQLITE_ENABLE_LOCKING_STYLE=0 -DSQLITE_WITHOUT_ZONEMALLOC
.endif

post-patch:
	${CP} ${.CURDIR}/${PHP_PKGSRC_README} ${WRKDIR}/${PHP_PKGSRC_README:T}
.if ${OPSYS} == "Darwin"
	${PATCH} -d ${WRKSRC} -p0 -F 0 < ${FILESDIR}/darwin-install-paths.patch
.endif

pre-configure:
	cd ${WRKSRC} && ${PKGSRC_SETENV} ${CONFIGURE_ENV} autoconf -f

post-install:
	cd ${WRKSRC}; ${INSTALL_DATA} php.ini-development php.ini-production \
		${DESTDIR}${PREFIX}/${PHP_EGDIR}
	${INSTALL_DATA} ${WRKDIR}/${PHP_PKGSRC_README:T} \
		${DESTDIR}${PREFIX}/${PHP_SHAREDIR}

.include "../../lang/php/phpversion.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "aarch64"
PKGREVISION=	1	# Reissue the withdrawn AArch64 package.
.endif
.include "../../mk/bsd.pkg.mk"
