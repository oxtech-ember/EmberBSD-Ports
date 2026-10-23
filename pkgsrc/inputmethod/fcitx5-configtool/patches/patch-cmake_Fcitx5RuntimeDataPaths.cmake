$NetBSD$

Separate discovered host paths from installed data locations.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- /dev/null
+++ cmake/Fcitx5RuntimeDataPaths.cmake
@@ -0,0 +1,9 @@
+# SPDX-License-Identifier: BSD-2-Clause
+# Origin: EmberBSD (AI-assisted).
+# Keep configure-time discovery paths separate from installed data paths.
+foreach(code 2 3 5)
+    set(ISOCODES_ISO639_${code}_JSON_RUNTIME "${ISOCODES_ISO639_${code}_JSON}" CACHE FILEPATH
+        "Installed iso_639-${code}.json path")
+endforeach()
+set(XKEYBOARDCONFIG_XKBBASE_RUNTIME "${XKEYBOARDCONFIG_XKBBASE}" CACHE PATH
+    "Installed xkeyboard-config base directory")
