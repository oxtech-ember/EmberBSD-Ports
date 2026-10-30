# $NetBSD: Makefile,v 1.87 2026/05/14 16:41:28 ryoon Exp $

DISTNAME=	libqalculate-5.13.1
PKGNAME=	qalculate-5.13.2
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITHUB:=Qalculate/}
GITHUB_PROJECT=	libqalculate
# 5.13.2 publishes Windows binaries only; apply its exact source commit.
GITHUB_RELEASE=	v5.13.1

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://qalculate.github.io/
COMMENT=	Modern multi-purpose desktop calculator (console version)
LICENSE=	gnu-gpl-v2

USE_CXX_FEATURES=	c++11
USE_LANGUAGES=		c c++
FORCE_CXX_STD=		gnu++17
USE_LIBTOOL=		yes
USE_PKGLOCALEDIR=	yes
USE_TOOLS+=		autoconf automake
USE_TOOLS+=		gmake msgfmt msgmerge xgettext pkg-config
GNU_CONFIGURE=		yes
CONFIGURE_ENV+=		ac_cv_prog_DOXYGEN=
PKGCONFIG_OVERRIDE=	libqalculate.pc.in

UNLIMIT_RESOURCES=	datasize

PREFER.gettext=	pkgsrc
PREFER.iconv=	pkgsrc
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if empty(EMBERBSD_CROSS_BUILD_CXX:U) || empty(EMBERBSD_CROSS_BUILD_CXX:M/*)
PKG_FAIL_REASON+= "Set EMBERBSD_CROSS_BUILD_CXX to the selected native C++ compiler"
.endif
CONFIGURE_ENV+= CXX_FOR_BUILD=${EMBERBSD_CROSS_BUILD_CXX:Q}
.endif

CFLAGS.SunOS+=		-D_LCONV_C99

pre-configure:
	cd ${WRKSRC} && autoreconf

.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../devel/readline/buildlink3.mk"
.include "../../math/mpfr/buildlink3.mk"
.include "../../textproc/icu/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../www/curl/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
