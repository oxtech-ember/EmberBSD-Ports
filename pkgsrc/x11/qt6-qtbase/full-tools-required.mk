# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). These Qt modules need a QtBase host with QtGui.
.if !defined(EMBERBSD_QTBASE_FULL_TOOLS_REQUIRED_MK)
EMBERBSD_QTBASE_FULL_TOOLS_REQUIRED_MK:=
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${PKG_BUILD_OPTIONS.qt6-qtbase:Mhost-tools}
PKG_FAIL_REASON+=	"This native Qt module requires full qt6-qtbase with QtGui; the host-tools option omits QtGui"
.endif
.endif
