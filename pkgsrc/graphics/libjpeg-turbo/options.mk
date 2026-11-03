# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
PKG_OPTIONS_VAR= PKG_OPTIONS.libjpeg-turbo
PKG_SUPPORTED_OPTIONS= tests

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mtests)
CMAKE_CONFIGURE_ARGS+= -DWITH_TESTS=ON
TEST_TARGET= test
.else
CMAKE_CONFIGURE_ARGS+= -DWITH_TESTS=OFF
do-test:
	@${FAIL_MSG} "Enable the tests package option before running tests."
	@${FALSE}
.endif
