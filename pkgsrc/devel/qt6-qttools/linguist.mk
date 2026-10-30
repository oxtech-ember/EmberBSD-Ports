# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Translation generators execute on the host.
# Include only for consumers of Linguist tools, not QtTools target libraries.
.if !defined(EMBERBSD_QT_LINGUIST_MK)
EMBERBSD_QT_LINGUIST_MK= yes
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.include "../../devel/qt6-qttools/host-tools.mk"
.else
BUILDLINK_DEPMETHOD.qt6-qttools?= build
.include "../../devel/qt6-qttools/buildlink3.mk"
.endif
.endif
