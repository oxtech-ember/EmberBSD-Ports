# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native KPackage tools for cross builds.
.if !defined(EMBERBSD_KF6_KPACKAGE_CROSS_MK)
EMBERBSD_KF6_KPACKAGE_CROSS_MK=	yes
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.include "../../meta-pkgs/kde/kf6-version.mk"
# KF6PackageConfig imports the native kpackagetool6 target export from
# KF6_HOST_TOOLING while cross-compiling. Build the matching host package.
TOOL_DEPENDS+=	kf6-kpackage-${KF6VER}{,nb[0-9]*}:../../devel/kf6-kpackage
.include "../../meta-pkgs/kde/host-tooling.mk"
.endif
.endif
