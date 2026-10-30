# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native KConfig code generators.
.if !defined(EMBERBSD_KF6_KCONFIG_CROSS_MK)
EMBERBSD_KF6_KCONFIG_CROSS_MK=	yes
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# KF6::kconfig_compiler and KF6::kconf_update run on the build host. They come
# from devel/kf6-kconfig-compiler, a native package of the same release, and
# KF6ConfigConfig.cmake imports them from KF6_HOST_TOOLING.
TOOL_DEPENDS+=	kf6-kconfig-compiler-6.31.0{,nb[0-9]*}:../../devel/kf6-kconfig-compiler
.include "../../meta-pkgs/kde/host-tooling.mk"
.endif
.endif
