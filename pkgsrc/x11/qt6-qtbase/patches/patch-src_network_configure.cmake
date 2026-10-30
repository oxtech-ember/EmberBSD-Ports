$NetBSD$

Use the common libpsl rule data and preserve Qt suffix policy.

--- src/network/configure.cmake.orig
+++ src/network/configure.cmake
@@ -381,18 +381,23 @@
     AUTODETECT NOT WASM
     DISABLE INPUT_publicsuffix STREQUAL "no"
 )
+qt_feature("publicsuffix-libpsl" PRIVATE
+    LABEL "  Common libpsl publicsuffix database"
+    CONDITION QT_FEATURE_topleveldomain
+    AUTODETECT OFF
+)
 qt_feature("publicsuffix-qt" PRIVATE
     LABEL "  Built-in publicsuffix database"
     CONDITION QT_FEATURE_topleveldomain
-    ENABLE INPUT_publicsuffix STREQUAL "qt" OR INPUT_publicsuffix STREQUAL "all"
-    DISABLE INPUT_publicsuffix STREQUAL "system"
+    ENABLE (INPUT_publicsuffix STREQUAL "qt" OR INPUT_publicsuffix STREQUAL "all") AND NOT QT_FEATURE_publicsuffix_libpsl
+    DISABLE INPUT_publicsuffix STREQUAL "system" OR QT_FEATURE_publicsuffix_libpsl
 )
 qt_feature("publicsuffix-system" PRIVATE
     LABEL "  System publicsuffix database"
     CONDITION QT_FEATURE_topleveldomain
     AUTODETECT LINUX OR HURD
-    ENABLE INPUT_publicsuffix STREQUAL "system" OR INPUT_publicsuffix STREQUAL "all"
-    DISABLE INPUT_publicsuffix STREQUAL "qt"
+    ENABLE (INPUT_publicsuffix STREQUAL "system" OR INPUT_publicsuffix STREQUAL "all") AND NOT QT_FEATURE_publicsuffix_libpsl
+    DISABLE INPUT_publicsuffix STREQUAL "qt" OR QT_FEATURE_publicsuffix_libpsl
 )
 
 qt_configure_add_summary_section(NAME "Qt Network")
@@ -418,6 +423,7 @@
 qt_configure_add_summary_entry(ARGS "gssapi")
 qt_configure_add_summary_entry(ARGS "brotli")
 qt_configure_add_summary_entry(ARGS "topleveldomain")
+qt_configure_add_summary_entry(ARGS "publicsuffix-libpsl")
 qt_configure_add_summary_entry(ARGS "publicsuffix-qt")
 qt_configure_add_summary_entry(ARGS "publicsuffix-system")
 qt_configure_end_summary_section() # end of "Qt Network" section
