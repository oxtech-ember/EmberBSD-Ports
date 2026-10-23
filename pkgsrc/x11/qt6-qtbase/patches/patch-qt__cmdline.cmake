$NetBSD: patch-qt__cmdline.cmake,v 1.1 2025/11/11 12:34:13 adam Exp $

Origin: pkgsrc; AI-assisted EmberBSD refresh for Qt 6.12.0, not submitted upstream.

Preserve the pkgsrc configure switch for its CMake/libarchive integration.

--- qt_cmdline.cmake.orig
+++ qt_cmdline.cmake
@@ -47,6 +47,7 @@
 qt_commandline_option(ohos-arch TYPE string CMAKE_VARIABLE OHOS_ARCH)
 qt_commandline_option(android-style-assets TYPE boolean)
 qt_commandline_option(appstore-compliant TYPE boolean)
+qt_commandline_option(avoid_cmake_archiving_api TYPE boolean CMAKE_VARIABLE QT_AVOID_CMAKE_ARCHIVING_API)
 qt_commandline_option(avx TYPE boolean)
 qt_commandline_option(avx2 TYPE boolean)
 qt_commandline_option(avx512 TYPE boolean NAME avx512f)
