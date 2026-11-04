# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
PKG_OPTIONS_VAR= PKG_OPTIONS.libdrm
PKG_SUPPORTED_OPTIONS= tests
PKG_SUGGESTED_OPTIONS= # none
.include "../../mk/bsd.options.mk"
.if !empty(PKG_OPTIONS:Mtests)
MESON_ARGS+= -Dtests=true
.else
MESON_ARGS+= -Dtests=false
pre-test:
	@${FAIL_MSG} "Enable the tests package option before running tests."
	@${FALSE}
.endif
