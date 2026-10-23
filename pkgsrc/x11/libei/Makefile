# $NetBSD: Makefile,v 1.3 2026/04/13 16:52:39 tnn Exp $

DISTNAME=		libei-1.6.0
PKGREVISION=		1
CATEGORIES=		x11 devel
MASTER_SITES=		https://gitlab.freedesktop.org/libinput/libei/-/archive/${PKGVERSION_NOREV}/
EXTRACT_SUFX=		.tar.bz2

# Origin: EmberBSD (AI-assisted). Pin the upstream test subproject.
MUNIT_REVISION=		fbbdf1467eb0d04a6ee465def2e529e4c87f2118
MUNIT_DISTFILE=		munit-${MUNIT_REVISION}.tar.gz
DISTFILES=		${DEFAULT_DISTFILES} ${MUNIT_DISTFILE}
SITES.${MUNIT_DISTFILE}=	-https://github.com/nemequ/munit/archive/${MUNIT_REVISION}.tar.gz

MAINTAINER=		pkgsrc-users@NetBSD.org
HOMEPAGE=		https://xorg.freedesktop.org/
COMMENT=		Library for Emulated Input
LICENSE=		mit

TOOL_DEPENDS+=		${PYPKGPREFIX}-jinja2-[0-9]*:../../textproc/py-jinja2
PYTHON_FOR_BUILD_ONLY=	tool
USE_TOOLS+=		pkg-config
USE_LANGUAGES=		c c++

NOT_FOR_PLATFORM+=	Darwin-*-*

CFLAGS.SunOS+=		-D_XOPEN_SOURCE=600	# CMSG_SPACE
CFLAGS.SunOS+=		-D__EXTENSIONS__=1	# strndup
LDFLAGS.SunOS+=		-lsocket

.include "../../mk/bsd.prefs.mk"

# Build all libraries and compiled tests. The auto setting only makes the
# upstream Python test modules optional; it does not disable the C tests.
MESON_ARGS+=		-Dlibei=enabled -Dlibeis=enabled -Dliboeffis=enabled
MESON_ARGS+=		-Dsd-bus-provider=basu -Dtests=auto

post-extract:
	${MV} ${WRKDIR}/munit-${MUNIT_REVISION} ${WRKSRC}/subprojects/munit

.if defined(OPSYS_HAS_KQUEUE)
CFLAGS+=	-I${BUILDLINK_PREFIX.libepoll-shim}/include/libepoll-shim
.include "../../devel/libepoll-shim/buildlink3.mk"
.endif
.include "../../devel/basu/buildlink3.mk"
.include "../../devel/input-headers/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../lang/python/tool.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
