# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
PKG_OPTIONS_VAR= PKG_OPTIONS.spirv-cross
PKG_SUPPORTED_OPTIONS= tests
.include "../../mk/bsd.options.mk"
.if !empty(PKG_OPTIONS:Mtests)
CMAKE_CONFIGURE_ARGS+= -DSPIRV_CROSS_ENABLE_TESTS=ON
TOOL_DEPENDS+= glslang>=16.6.0:../../graphics/glslang
TOOL_DEPENDS+= spirv-tools>=2026.4nb3:../../parallel/spirv-tools
CMAKE_CONFIGURE_ARGS+= -Dspirv-cross-glslang:FILEPATH=${TOOLBASE}/bin/glslangValidator
CMAKE_CONFIGURE_ARGS+= -Dspirv-cross-spirv-as:FILEPATH=${TOOLBASE}/bin/spirv-as
CMAKE_CONFIGURE_ARGS+= -Dspirv-cross-spirv-val:FILEPATH=${TOOLBASE}/bin/spirv-val
CMAKE_CONFIGURE_ARGS+= -Dspirv-cross-spirv-opt:FILEPATH=${TOOLBASE}/bin/spirv-opt
pre-configure:
.for _test_tool in glslangValidator spirv-as spirv-val spirv-opt
	@${TEST} -x ${TOOLBASE}/bin/${_test_tool} || { \
		${ERROR_MSG} "Missing selected SPIRV-Cross test tool: ${_test_tool}"; exit 1; }
.endfor
TEST_TARGET= test
.else
CMAKE_CONFIGURE_ARGS+= -DSPIRV_CROSS_ENABLE_TESTS=OFF
do-test:
	@${FAIL_MSG} "Enable the tests package option before running tests."
	@${FALSE}
.endif
