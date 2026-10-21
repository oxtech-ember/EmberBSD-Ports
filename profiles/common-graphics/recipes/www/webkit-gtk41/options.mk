# $NetBSD: options.mk,v 1.1 2026/08/30 14:25:05 wiz Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.webkit-gtk
PKG_SUPPORTED_OPTIONS=	debug wayland webkit-jit webkit-developer-mode webkit-webdriver
PKG_SUGGESTED_OPTIONS=

.include "../../devel/wayland/platform.mk"

.if ${PLATFORM_SUPPORTS_WAYLAND} == "yes"
PKG_SUGGESTED_OPTIONS+=	wayland
.endif

.include "../../mk/bsd.fast.prefs.mk"

#
# Platforms that support the webkit-jit option
#
# Please see:
#  Source/cmake/WebKitFeatures.cmake
#  Source/WTF/wtf/PlatformEnable.h
#
WEBKIT_JIT_MACHINE_PLATFORMS+=	Darwin-*-*
WEBKIT_JIT_MACHINE_PLATFORMS+=	DragonFly-*-*
WEBKIT_JIT_MACHINE_PLATFORMS+=	FreeBSD-*-x86_64 FreeBSD-*-aarch64
WEBKIT_JIT_MACHINE_PLATFORMS+=	Linux-*-x86_64 Linux-*-arm*
WEBKIT_JIT_MACHINE_PLATFORMS+=	Linux-*-aarch64 Linux-*-mips*
WEBKIT_JIT_MACHINE_PLATFORMS+=	NetBSD-*-x86_64 NetBSD-*-aarch64

.if !empty(WEBKIT_JIT_MACHINE_PLATFORMS:@.PLAT.@${MACHINE_PLATFORM:M${.PLAT.}}@)
# The canonical package leaves JIT opt-in because of its OpcodeOrigin
# compilation boundary. Preserve that choice until a real current JIT build
# validates a repair; C-loop and the opt-in option remain available.
#PKG_SUGGESTED_OPTIONS+=	webkit-jit
.endif

.include "../../mk/bsd.options.mk"

#
# JIT support
#
.if !empty(PKG_OPTIONS:Mwebkit-jit)
CMAKE_CONFIGURE_ARGS+=	-DENABLE_JIT=ON
CMAKE_CONFIGURE_ARGS+=	-DENABLE_C_LOOP=OFF
.else
CMAKE_CONFIGURE_ARGS+=	-DENABLE_JIT=OFF
CMAKE_CONFIGURE_ARGS+=	-DENABLE_C_LOOP=ON
.endif

#
# Debug build
#
.if !empty(PKG_OPTIONS:Mdebug)
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Debug
INSTALL_UNSTRIPPED=	yes
# This does not disable optimisations, merely avoids #error if there are none.
#CFLAGS+=		-DRELEASE_WITHOUT_OPTIMIZATIONS
.else
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
# Keep the GCC16 cross-build optimized while avoiding WebKit's unusually slow
# default -O3 passes on the large unified JavaScriptCore/WebCore translation units.
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_C_FLAGS_RELEASE:STRING=-O2\ -DNDEBUG
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_CXX_FLAGS_RELEASE:STRING=-O2\ -DNDEBUG
.endif

#
# Wayland display server support
#
.if !empty(PKG_OPTIONS:Mwayland)
CMAKE_CONFIGURE_ARGS+=	-DENABLE_WAYLAND_TARGET=ON
.include "../../devel/wayland/buildlink3.mk"
.else
CMAKE_CONFIGURE_ARGS+=	-DENABLE_WAYLAND_TARGET=OFF
.endif

# DEVELOPER_MODE enables WEBKIT_EXEC_PATH env var so MiniBrowser can be run
# from the build tree without installing; also auto-discovers helpers next to
# the MiniBrowser binary itself.
.if !empty(PKG_OPTIONS:Mwebkit-developer-mode)
CMAKE_CONFIGURE_ARGS+=		-DDEVELOPER_MODE=ON
# DEVELOPER_MODE defaults ENABLE_API_TESTS and ENABLE_LAYOUT_TESTS to ON, but
# the release tarball does not ship those test sources; disable them explicitly.
# CLANGD_AUTO_SETUP is also enabled by DEVELOPER_MODE but requires Tools/clangd/
# scripts not present in the tarball.
CMAKE_CONFIGURE_ARGS+=		-DENABLE_API_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=		-DENABLE_LAYOUT_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=		-DCLANGD_AUTO_SETUP=OFF
CMAKE_CONFIGURE_ARGS+=		-DDEVELOPER_MODE_FATAL_WARNINGS=OFF
.endif

#
# Tool for interacting with the browser from Python. Mostly for testing.
#
.if !empty(PKG_OPTIONS:Mwebkit-webdriver)
CMAKE_CONFIGURE_ARGS+=	-DENABLE_WEBDRIVER=ON
PLIST_SRC+=		${.CURDIR}/../../www/webkit-gtk41/PLIST.webdriver
.else
CMAKE_CONFIGURE_ARGS+=	-DENABLE_WEBDRIVER=OFF
.endif
