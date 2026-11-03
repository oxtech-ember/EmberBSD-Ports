# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
PKG_OPTIONS_VAR= PKG_OPTIONS.glib2-introspection
PKG_SUPPORTED_OPTIONS= tests
.include "../../mk/bsd.options.mk"
.if !empty(PKG_OPTIONS:Mtests)
MESON_ARGS+= -Dtests=true
.else
MESON_ARGS+= -Dtests=false
.endif
