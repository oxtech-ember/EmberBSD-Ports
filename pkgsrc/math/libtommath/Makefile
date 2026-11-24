# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= libtommath-1.3.0
CATEGORIES= math
MASTER_SITES= ${MASTER_SITE_GITHUB:=libtom/}
GITHUB_TAG= v${PKGVERSION_NOREV}
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/libtom/libtommath/
COMMENT= Portable multiple-precision integer library
LICENSE= unlicense
USE_LANGUAGES= c
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON
PLIST_VARS+= darwin unix
.include "../../mk/bsd.prefs.mk"
.include "options.mk"
.if ${OPSYS} == "Darwin"
PLIST.darwin= yes
.else
PLIST.unix= yes
.endif
.include "../../devel/cmake/build.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "aarch64"
PKGREVISION=	1	# Require the libc SONAME on AArch64.
.endif

.include "../../mk/bsd.pkg.mk"
