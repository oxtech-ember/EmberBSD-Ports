# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
PKG_OPTIONS_VAR= PKG_OPTIONS.libspng
PKG_SUPPORTED_OPTIONS= examples

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mexamples)
CMAKE_CONFIGURE_ARGS+= -DBUILD_EXAMPLES=ON
.else
CMAKE_CONFIGURE_ARGS+= -DBUILD_EXAMPLES=OFF
.endif
