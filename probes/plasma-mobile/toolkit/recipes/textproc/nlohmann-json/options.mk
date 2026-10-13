# $NetBSD: options.mk,v 1.3 2025/04/20 19:26:10 wiz Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.nlohmann-json

PKG_SUPPORTED_OPTIONS=	tests

.include "../../mk/bsd.options.mk"

PLIST_VARS+=		tests
.if !empty(PKG_OPTIONS:Mtests)
# Match the test-data version selected by upstream CMake.
# Fetch it through pkgsrc checksums instead of cloning during a test.
DISTFILES+=		json_test_data-3.1.0.tar.gz
SITES.json_test_data-3.1.0.tar.gz= -https://github.com/nlohmann/json_test_data/archive/refs/tags/v3.1.0.tar.gz
CMAKE_CONFIGURE_ARGS+=	-DJSON_TestDataDirectory=${WRKDIR}/json_test_data-3.1.0
PLIST.tests=		yes
TEST_TARGET=		test
CMAKE_CONFIGURE_ARGS+=	-DJSON_BuildTests=ON
.else
CMAKE_CONFIGURE_ARGS+=	-DJSON_BuildTests=OFF
.endif
