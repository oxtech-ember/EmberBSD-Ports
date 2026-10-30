# $NetBSD: Makefile,v 1.73 2026/09/02 19:04:59 wiz Exp $

DISTNAME=	libproxy-0.5.12
PKGREVISION=	8
CATEGORIES=	www gnome
MASTER_SITES=	${MASTER_SITE_GITHUB:=libproxy/}
GITHUB_TAG=	${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://libproxy.github.io/libproxy/
COMMENT=	Library that provides automatic proxy configuration management
LICENSE=	gnu-lgpl-v2.1

BUILD_DEPENDS+=	glib2-introspection>=2.90.1nb1:../../devel/glib2-introspection

USE_CC_FEATURES=	c99
USE_CXX_FEATURES=	c++11
USE_LANGUAGES=		c c++
USE_TOOLS+=		bash:build pkg-config

# Release tarballs must not try to install a developer Git hook.
MESON_ARGS+=	-Drelease=true

PKGCONFIG_OVERRIDE+=		output/meson-private/libproxy-1.0.pc
PKGCONFIG_OVERRIDE_STAGE=	post-configure

# For Darwin
TEST_ENV+=	DYLD_LIBRARY_PATH=${WRKSRC}/output/src/backend:${WRKSRC}/output/src/libproxy
TEST_TARGET=	test

REPLACE_BASH+=	data/check-code-style
REPLACE_BASH+=	data/install-git-hook.sh
REPLACE_BASH+=	data/pre-commit-hook

# shouldn't be necessary, but is?
# https://github.com/libproxy/libproxy/issues/237
LDFLAGS+=	${COMPILER_RPATH_FLAG}${PREFIX}/lib/libproxy

.include "../../mk/bsd.prefs.mk"
.include "options.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
EMBERBSD_GI_MESON_OPTIONS= no
MAKE_ENV+= XDG_DATA_DIRS=${CROSS_DESTDIR:Q}${PREFIX:Q}/share
.include "../../devel/gobject-introspection/cross.mk"
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper emberbsd_vapi_dir
MESON_CROSS.emberbsd_vapi_dir= '${TOOLBASE}/share/vala-0.56/vapi'
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
EMBERBSD_LIBPROXY_REAL_SYSROOT!= cd ${CROSS_DESTDIR:Q} && pwd -P
BUILDLINK_TRANSFORM+= I:${EMBERBSD_LIBPROXY_REAL_SYSROOT}${PREFIX}:${BUILDLINK_DIR}
.endif
.include "../../devel/meson/build.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../lang/libduktape/buildlink3.mk"
.include "../../sysutils/gsettings-desktop-schemas/buildlink3.mk"
.include "../../www/curl/buildlink3.mk"
.include "../../mk/dlopen.buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
