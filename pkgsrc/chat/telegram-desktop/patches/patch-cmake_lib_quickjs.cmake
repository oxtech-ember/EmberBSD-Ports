--- Telegram/cmake/lib_quickjs.cmake.orig
+++ Telegram/cmake/lib_quickjs.cmake
@@ -3,6 +3,50 @@
 #
 # For license and copyright information please follow this link:
 # https://github.com/telegramdesktop/tdesktop/blob/master/LEGAL
+
+
+# EmberBSD ships the pinned QuickJS-ng fork as one shared Ports package.
+# Keep the widget-sandbox C shim at the consumer and link only the engine from
+# the common provider. Other Telegram Desktop platforms retain their upstream
+# source build below.
+if (CMAKE_SYSTEM_NAME STREQUAL "NetBSD")
+    find_package(PkgConfig REQUIRED)
+    pkg_check_modules(QUICKJS_NG REQUIRED IMPORTED_TARGET quickjs-ng)
+
+    add_library(lib_quickjs STATIC)
+    init_target(lib_quickjs "(external)")
+    add_library(tdesktop::lib_quickjs ALIAS lib_quickjs)
+
+    set(quickjs_root ${third_party_loc}/widget-sandbox/packages/ios/Sources/CQuickJS)
+    if (NOT EXISTS ${quickjs_root}/shim/qjs_shim.c OR NOT EXISTS ${quickjs_root}/include/qjs_shim.h)
+        message(FATAL_ERROR "QuickJS-ng shim sources are missing, run 'git submodule update --init --recursive'.")
+    endif()
+
+    # Adapt only the generated build-tree header: the upstream shim's relative
+    # include names the private core path, while Ports installs quickjs.h in a
+    # collision-free namespace.
+    file(READ ${quickjs_root}/include/qjs_shim.h qjs_shim_header)
+    string(REPLACE "\"../quickjs/quickjs.h\"" "<quickjs.h>" qjs_shim_header "${qjs_shim_header}")
+    file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/qjs_shim.h "${qjs_shim_header}")
+
+    nice_target_sources(lib_quickjs ${quickjs_root}
+    PRIVATE
+        shim/qjs_shim.c
+    )
+
+    set_target_properties(lib_quickjs PROPERTIES
+        C_STANDARD 11
+        C_STANDARD_REQUIRED ON
+        C_EXTENSIONS ON
+    )
+
+    target_include_directories(lib_quickjs BEFORE PUBLIC
+        ${CMAKE_CURRENT_BINARY_DIR}
+    )
+    target_compile_definitions(lib_quickjs PRIVATE _GNU_SOURCE)
+    target_compile_options(lib_quickjs PRIVATE -funsigned-char -w)
+    target_link_libraries(lib_quickjs PUBLIC PkgConfig::QUICKJS_NG)
+else()
 
 # QuickJS-ng as the TelegramMessenger/quickjs fork, a nested submodule of
 # ThirdParty/widget-sandbox: the engine its shared sandbox and validator
@@ -97,3 +141,5 @@
         -w
     )
 endif()
+
+endif()
