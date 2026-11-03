# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
PKG_OPTIONS_VAR= PKG_OPTIONS.libtommath
PKG_SUPPORTED_OPTIONS= tests

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mtests)
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=ON
TEST_TARGET= test
.else
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=OFF
do-test:
	@${FAIL_MSG} "Enable the tests package option before running tests."
	@${FALSE}
.endif
