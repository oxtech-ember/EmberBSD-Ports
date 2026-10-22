# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).

.include "../../mk/bsd.prefs.mk"

PKG_OPTIONS_VAR=		PKG_OPTIONS.libsecret
PKG_SUPPORTED_OPTIONS=	doc
PKG_SUGGESTED_OPTIONS=

# This older cross recipe does not generate the GIR needed by the API site.
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
PKG_SUGGESTED_OPTIONS+=	doc
.endif

.include "../../mk/bsd.options.mk"

PLIST_VARS+=	doc
.if !empty(PKG_OPTIONS:Mdoc)
PLIST.doc=	yes
MESON_ARGS+=	-Dgtk_doc=true
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+= "The common libsecret cross recipe cannot generate the GIR required by documentation"
.else
.include "../../devel/py-gi-docgen/buildlink3.mk"
.endif
.else
MESON_ARGS+=	-Dgtk_doc=false
.endif
