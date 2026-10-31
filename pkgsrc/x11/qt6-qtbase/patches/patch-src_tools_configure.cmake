$NetBSD$

Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

Find the explicitly selected native scanner on Darwin.

--- src/tools/configure.cmake
+++ src/tools/configure.cmake
@@ -1,7 +1,7 @@
 # Copyright (C) 2022 The Qt Company Ltd.
 # SPDX-License-Identifier: BSD-3-Clause
 
-if(LINUX OR QT_FIND_ALL_PACKAGES_ALWAYS)
+if(LINUX OR QT_FIND_ALL_PACKAGES_ALWAYS OR (APPLE AND EMBERBSD_FIND_WAYLAND_SCANNER))
     qt_find_package(WaylandScanner MODULE PROVIDED_TARGETS Wayland::Scanner)
 endif()
 
