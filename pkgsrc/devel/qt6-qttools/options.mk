# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Native Linguist tools and qtattributionsscanner for Qt cross builds.
# Cross qttools imports Qt6LinguistTools and Qt6ToolsTools from them.

PKG_OPTIONS_VAR=	PKG_OPTIONS.qt6-qttools

.include "../../mk/bsd.fast.prefs.mk"

# host-tools is the only option. Cross builds have none and skip bsd.options.mk.
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
PKG_SUPPORTED_OPTIONS+=	host-tools
.include "../../mk/bsd.options.mk"
.endif

.if !empty(PKG_OPTIONS:Mhost-tools)
PLIST_SRC=		${PKGDIR}/PLIST.host-tools
.  for _feature_ in assistant designer distancefieldgenerator kmap2qmap \
	objcnamemangler pixeltool qdbus qev qtdiag \
	qtplugininfo
CMAKE_CONFIGURE_ARGS+=	-DFEATURE_${_feature_}=OFF
.  endfor
CMAKE_CONFIGURE_ARGS+=	-DFEATURE_linguist=ON -DFEATURE_qtattributionsscanner=ON
.endif
