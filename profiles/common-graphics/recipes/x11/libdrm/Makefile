# $NetBSD: Makefile,v 1.126 2026/05/29 09:02:25 wiz Exp $
# Origin: EmberBSD; AI-assisted matched native-identity source candidate.
DISTNAME=	libdrm-2.4.134
PKGREVISION=	3
CATEGORIES=	x11 graphics
MASTER_SITES=	https://dri.freedesktop.org/libdrm/
EXTRACT_SUFX=	.tar.xz
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://dri.freedesktop.org/wiki/DRM
COMMENT=	Userspace interface to kernel DRM services
LICENSE=	mit
ONLY_FOR_PLATFORM=	NetBSD-11.*-aarch64 NetBSD-11.*-x86_64
USE_TOOLS+=	pkg-config
# Retain diagnostics for unsupported buses; all other warnings are fatal.
CFLAGS+=	-Werror -Wno-error=cpp
USE_LANGUAGES=	c
USE_CC_FEATURES+=	c11
GCC_REQD+=	16.2
MESON_REQD+=	1.12.1
PYTHON_FOR_BUILD_ONLY=	tool
PYTHON_VERSION_REQD=	314
PKGCONFIG_OVERRIDE+=	libdrm.pc.in
.include "../../mk/bsd.prefs.mk"
.if !defined(EMBERBSD_COMMON_GRAPHICS)
PKG_FAIL_REASON+= "libdrm requires the prepared common graphics profile"
.endif
.if ${DISTNAME} != "libdrm-2.4.134" || ${PKGREVISION} != "3"
PKG_FAIL_REASON+= "The common graphics profile requires adapted libdrm 2.4.134nb3"
.endif
SUBST_CLASSES+=	atomic
SUBST_FILES.atomic=	xf86drm.h
SUBST_MESSAGE.atomic=	Configuring atomic operations in xf86drm.h
SUBST_STAGE.atomic=	pre-configure
SUBST_VARS.atomic=	ATOMIC_OPS_CHECK
ATOMIC_OPS_CHECK=	0
.if exists(${_CROSS_DESTDIR}/usr/include/sys/atomic.h)
ATOMIC_OPS_CHECK=	1
.else
.include "../../devel/libatomic_ops/buildlink3.mk"
.endif
PLIST_VARS+= intel
.if ${MACHINE_ARCH} == "x86_64"
MESON_ARGS+=	-Dintel=enabled
PLIST.intel=	yes
.include "../../sysutils/libpciaccess/buildlink3.mk"
.else
MESON_ARGS+=	-Dintel=disabled
.endif
.for module in radeon amdgpu nouveau vmwgfx omap exynos freedreno tegra vc4 etnaviv
MESON_ARGS+=	-D${module}=disabled
.endfor
MESON_ARGS+=	-Dman-pages=disabled -Dcairo-tests=disabled -Dvalgrind=disabled
MESON_ARGS+=	-Dtests=true -Dinstall-test-programs=false
# pkgsrc supplies --buildtype=plain and the selected compiler optimization.
MESON_ARGS+=	-Db_lto=false -Dwerror=true
LDFLAGS.NetBSD+=	-lpci
# Unlike unmodified pkgsrc, common libdrm must also build with native X11.
# Do not include modular-xorg/avoid-duplicate.mk here.
.include "../../lang/python/tool.mk"
# Bind the upstream Python module and symbol-test shebang to one interpreter.
MESON_BINARIES+= python
MESON_BINARY.python= ${TOOL_PYTHONBIN}
REPLACE_TOOL_PYTHON+= symbols-check.py gen_table_fourcc.py
.include "../../lang/python/application.mk"
pre-configure:
	${TEST} -x ${TOOL_PYTHONBIN:Q}
	${TOOL_PYTHONBIN} -c 'import sys; assert sys.version_info[:2] == (3, 14)'
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
