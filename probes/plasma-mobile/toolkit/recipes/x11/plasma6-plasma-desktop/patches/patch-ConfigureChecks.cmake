$NetBSD$

Use the canonical XKB root before the legacy X11 compatibility alias.
Handle pkgconf sysroot prefixes in the XKB data variable.
Store the target path in config-workspace.h for the keyboard preview.
Check the real directory in the sysroot without using a host fallback.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- ConfigureChecks.cmake.orig
+++ ConfigureChecks.cmake
@@ -1,13 +1,38 @@
 set(CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake/modules ${CMAKE_MODULE_PATH} )
 
-pkg_get_variable(XKBDIR xkeyboard-config xkb_base)
+# xkb_root is canonical. xkb_base can be an absolute compatibility symlink
+# whose target is valid only inside the target filesystem.
+pkg_get_variable(XKBDIR xkeyboard-config xkb_root)
 if (NOT XKBDIR)
-    message(FATAL_ERROR "Couldn't find xkb_base using pkg-config: is xkeyboard-config installed?")
-elseif (CMAKE_CROSSCOMPILING)
-    if (NOT EXISTS "${CMAKE_SYSROOT}/${XKBDIR}")
-      message(FATAL_ERROR "Couldn't find XKB location in CMAKE_SYSROOT: \"${CMAKE_SYSROOT}/${XKBDIR}\"")
+    pkg_get_variable(XKBDIR xkeyboard-config xkb_base)
+endif()
+if (NOT XKBDIR)
+    message(FATAL_ERROR "Couldn't find xkb_root or xkb_base using pkg-config: is xkeyboard-config installed?")
+elseif (NOT IS_ABSOLUTE "${XKBDIR}")
+    message(FATAL_ERROR "XKB location must be absolute: \"${XKBDIR}\".")
+endif()
+get_filename_component(XKBDIR "${XKBDIR}" ABSOLUTE)
+if (CMAKE_CROSSCOMPILING)
+    if (NOT IS_ABSOLUTE "${CMAKE_SYSROOT}")
+        message(FATAL_ERROR "Cross XKB lookup requires an absolute CMAKE_SYSROOT.")
+    endif()
+    get_filename_component(_xkb_sysroot "${CMAKE_SYSROOT}" ABSOLUTE)
+    # pkgconf can return an already rooted absolute variable. Keep the target
+    # path in config-workspace.h, but check its directory inside the sysroot.
+    if (NOT _xkb_sysroot STREQUAL "/")
+        string(FIND "${XKBDIR}/" "${_xkb_sysroot}/" _xkb_root_at)
+        if (_xkb_root_at EQUAL 0)
+            string(LENGTH "${_xkb_sysroot}" _xkb_root_length)
+            string(SUBSTRING "${XKBDIR}" ${_xkb_root_length} -1 XKBDIR)
+            if (XKBDIR STREQUAL "")
+                set(XKBDIR "/")
+            endif()
+        endif()
+    endif()
+    if (NOT IS_DIRECTORY "${_xkb_sysroot}${XKBDIR}")
+        message(FATAL_ERROR "Couldn't find XKB location in CMAKE_SYSROOT: \"${_xkb_sysroot}${XKBDIR}\"")
     endif()
-elseif(NOT EXISTS "${XKBDIR}")
+elseif (NOT IS_DIRECTORY "${XKBDIR}")
     message(FATAL_ERROR "Couldn't find XKB location: \"${XKBDIR}\".")
 endif()
 
