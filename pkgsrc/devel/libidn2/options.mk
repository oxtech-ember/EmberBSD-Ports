# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
PKG_OPTIONS_VAR= PKG_OPTIONS.libidn2
PKG_SUPPORTED_OPTIONS= examples
.include "../../mk/bsd.options.mk"
.if empty(PKG_OPTIONS:Mexamples)
MAKE_FLAGS+= EXAMPLES_SUBDIR=
.endif
