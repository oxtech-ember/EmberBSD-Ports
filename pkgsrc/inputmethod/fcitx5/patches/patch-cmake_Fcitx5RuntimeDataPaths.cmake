$NetBSD$

Separate discovered host paths from installed data locations.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- /dev/null
+++ cmake/Fcitx5RuntimeDataPaths.cmake
@@ -0,0 +1,9 @@
+# SPDX-License-Identifier: BSD-2-Clause
+# Origin: EmberBSD (AI-assisted).
+# Keep configure-time discovery paths separate from installed data paths.
+set(ISOCODES_ISO639_JSON_RUNTIME "${ISOCODES_ISO639_JSON}" CACHE FILEPATH
+    "Installed iso_639-3.json path")
+set(XKEYBOARDCONFIG_XKBBASE_RUNTIME "${XKEYBOARDCONFIG_XKBBASE}" CACHE PATH
+    "Installed xkeyboard-config base directory")
+set(XKEYBOARDCONFIG_DATADIR_RUNTIME "${XKEYBOARDCONFIG_DATADIR}" CACHE PATH
+    "Installed xkeyboard-config data directory")
