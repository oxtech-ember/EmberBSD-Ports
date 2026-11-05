PKG_OPTIONS_VAR= PKG_OPTIONS.libmysofa
PKG_SUPPORTED_OPTIONS= tests
PLIST_VARS+= tests
.include "../../mk/bsd.options.mk"
.if !empty(PKG_OPTIONS:Mtests)
PLIST.tests= yes
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTS=ON
TEST_DEPENDS+= nodejs-[0-9]*:../../lang/nodejs
TEST_TARGET= test
BUILDLINK_DEPMETHOD.cunit= build
.include "../../devel/cunit/buildlink3.mk"
.else
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTS=OFF
.endif
