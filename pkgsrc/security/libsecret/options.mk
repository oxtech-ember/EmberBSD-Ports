# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).

PKG_OPTIONS_VAR=		PKG_OPTIONS.libsecret
PKG_SUPPORTED_OPTIONS=	doc
PKG_SUGGESTED_OPTIONS=	doc

.include "../../mk/bsd.options.mk"

PLIST_VARS+=	doc
.if !empty(PKG_OPTIONS:Mdoc)
PLIST.doc=	yes
MESON_ARGS+=	-Dgtk_doc=true
.else
MESON_ARGS+=	-Dgtk_doc=false
.endif
