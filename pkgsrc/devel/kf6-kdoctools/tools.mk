# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), cross documentation consumer dependency.
.include "../../mk/bsd.prefs.mk"
.include "../../meta-pkgs/kde/kf6-version.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
BUILDLINK_DEPMETHOD.kf6-kdoctools?= build
.include "../../devel/kf6-kdoctools/buildlink3.mk"
.else
TOOL_DEPENDS+= kf6-kdoctools-generators-${KF6VER}{,nb[0-9]*}:../../devel/kf6-kdoctools-generators
.endif
