# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native KCMUtils desktop file generator.
.if !defined(EMBERBSD_KF6_KCMUTILS_CROSS_MK)
EMBERBSD_KF6_KCMUTILS_CROSS_MK=	yes
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# KF6::kcmdesktopfilegenerator runs on the build host. It comes from
# devel/kf6-kcmutils-tools, a native package of the same release, and
# KF6KCMUtilsConfig.cmake imports it from KF6_HOST_TOOLING.
TOOL_DEPENDS+=	kf6-kcmutils-tools-6.31.0{,nb[0-9]*}:../../devel/kf6-kcmutils-tools
.include "../../meta-pkgs/kde/host-tooling.mk"
.endif
.endif
