# $NetBSD: Makefile,v 1.66 2024/04/30 12:06:15 cheusov Exp $

DISTNAME=	flex-2.7.3
CATEGORIES=	devel lang
MASTER_SITES=	${MASTER_SITE_GITHUB:=westes/}
GITHUB_RELEASE=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/westes/flex
COMMENT=	Fast clone of lex(1), the lexical scanner generator
LICENSE=	2-clause-bsd

TOOL_DEPENDS+=		help2man-[0-9]*:../../converters/help2man

# wants stdbool
USE_LANGUAGES=		c99 c++

USE_LIBTOOL=		yes
USE_PKGLOCALEDIR=	yes
USE_TOOLS+=		gm4:run	gmake makeinfo
GNU_CONFIGURE=		yes
INFO_FILES=		yes
PKGCONFIG_OVERRIDE+=	src/libfl.pc.in

TEST_TARGET=		check
LIBS.SunOS+=		-lm

.include "../../mk/bsd.prefs.mk"

.if ${OPSYS} == "Darwin"
PKGREVISION=		1
# The build scanner uses the selected build tool. Installed flex finds the
# runtime tool and message catalogs relative to its own executable.
MAKE_ENV+=		M4=${TOOLS_PATH.gm4:Q}
CPPFLAGS+=		-DFLEX_DARWIN_M4=\"${TOOLS_PATH.gm4:T}\"
CPPFLAGS+=		-DFLEX_DARWIN_LOCALEDIR=\"${PKGLOCALEDIR}/locale\"
.endif

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && \
    !empty(OS_VERSION:M11.*)
# The build scanner uses host gm4. The installed scanner uses base m4.
PKGREVISION=		1
USE_TOOLS:=		${USE_TOOLS:Ngm4\:run} gm4
MAKE_ENV+=		M4=${TOOLS_PATH.gm4:Q}
CPPFLAGS+=		-DFLEX_TARGET_M4=\"/usr/bin/m4\"
.endif

CFLAGS.AIX+=		-D_LINUX_SOURCE_COMPAT

.if ${OS_VARIANT} == "SCOOSR5"
LDFLAGS.SCO_SV+=	-lsocket
.endif

.include "options.mk"

# https://github.com/westes/flex/issues/219
CONFIGURE_ENV.NetBSD+=	ac_cv_func_reallocarray=no

# https://github.com/westes/flex/issues/241
CFLAGS.Linux+=		-D_GNU_SOURCE

.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
