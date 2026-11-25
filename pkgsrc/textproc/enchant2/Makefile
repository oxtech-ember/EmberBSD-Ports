# $NetBSD: Makefile,v 1.62 2026/09/07 08:11:23 adam Exp $

DISTNAME=	enchant-2.8.21
PKGNAME=	${DISTNAME:S/enchant/enchant2/}
PKGREVISION=	1
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=rrthomas/}
GITHUB_PROJECT=	enchant
GITHUB_RELEASE=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://rrthomas.github.io/enchant/
COMMENT=	Generic spell checking library
LICENSE=	gnu-lgpl-v2.1

USE_CXX_FEATURES=	c++11
USE_LANGUAGES=		c c++
USE_PKGLOCALEDIR=	yes
USE_LIBTOOL=		yes
USE_TOOLS+=		autoconf gmake groff pkg-config
PKGCONFIG_OVERRIDE+=	enchant.pc.in
GNU_CONFIGURE=		yes
CFLAGS.SunOS+=		-D__EXTENSIONS__

# Force disable all spell checkers that are not handled in options.mk,
# to avoid them being unintentionally found if installed.
CONFIGURE_ARGS+=	--without-hspell	# Hebrew
CONFIGURE_ARGS+=	--without-nuspell
CONFIGURE_ARGS+=	--without-voikko	# Finnish

# \todo The package previously relied on finding applespell on mac,
# without forcing it on, and without explaining this.  Change to
# enable on mac (but not on darwin without mac!).
#CONFIGURE_ARGS+=	--without-applespell

# needed for testing
CONFIGURE_ARGS+=	--enable-relocatable
TEST_TARGET=		check

# HTML manuals need a native groff during a cross build.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && defined(EMBERBSD_BUILD_GROFF)
.if empty(EMBERBSD_BUILD_GROFF:M/*) || !exists(${EMBERBSD_BUILD_GROFF})
PKG_FAIL_REASON+= "Set EMBERBSD_BUILD_GROFF to an absolute native groff executable"
.endif
TOOLS_PLATFORM.groff= ${EMBERBSD_BUILD_GROFF}
# pkgsrc runs a symlink in .tools/bin. Preserve groff's sibling tools.
MAKE_ENV+= GROFF_BIN_PATH=${EMBERBSD_BUILD_GROFF:H}
.endif

.include "options.mk"


BUILDLINK_API_DEPENDS.glib2+=	glib2>=2.76
.include "../../devel/glib2/buildlink3.mk"
.if !empty(PKGSRC_RUN_TEST:M[yY][eE][sS]) || make(test) || make(retest)
BUILDLINK_DEPMETHOD.unittest-cpp=	build
.include "../../devel/unittest-cpp/buildlink3.mk"
# A work directory configured by a regular build has no UnitTest++ flags.
TEST_MAKE_FLAGS+=	UNITTESTPP_LIBS=-lUnitTest++
pre-test:
	${RUN} if ${TEST} ! -f ${BUILDLINK_DIR:Q}/.buildlink_unittest-cpp_done; then \
		${RECURSIVE_MAKE} ${MAKEFLAGS} PKGSRC_RUN_TEST=yes depends-clean && \
		${RECURSIVE_MAKE} ${MAKEFLAGS} PKGSRC_RUN_TEST=yes depends && \
		${RECURSIVE_MAKE} ${MAKEFLAGS} PKGSRC_RUN_TEST=yes buildlink-unittest-cpp; \
	fi
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && \
    (${MACHINE_ARCH} == "aarch64" || ${MACHINE_ARCH} == "x86_64")
PKGREVISION=	2	# Record the base libc SONAME.
.endif

.include "../../mk/bsd.pkg.mk"
