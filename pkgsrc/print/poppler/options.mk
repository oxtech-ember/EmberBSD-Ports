# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).

PKG_OPTIONS_VAR=		PKG_OPTIONS.poppler
PKG_SUPPORTED_OPTIONS=	tests

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mtests)
CMAKE_CONFIGURE_ARGS+=	-DBUILD_MANUAL_TESTS=ON
.else
CMAKE_CONFIGURE_ARGS+=	-DBUILD_MANUAL_TESTS=OFF
.endif
