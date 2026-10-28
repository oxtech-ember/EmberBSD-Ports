$NetBSD$

Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
Use the selected CMAKE_OSX_SYSROOT and its SDKSettings.json instead of xcrun.
Skip the Xcode query when the Xcode version check is disabled.

--- cmake/QtPublicAppleHelpers.cmake.orig
+++ cmake/QtPublicAppleHelpers.cmake
@@ -914,7 +914,9 @@
 
 function(_qt_internal_get_apple_sdk_path out_var)
     set(sdk_path "")
-    if(APPLE)
+    if(APPLE AND IS_ABSOLUTE "${CMAKE_OSX_SYSROOT}" AND IS_DIRECTORY "${CMAKE_OSX_SYSROOT}")
+        set(sdk_path "${CMAKE_OSX_SYSROOT}")
+    elseif(APPLE)
         _qt_internal_get_apple_sdk_name(sdk_name)
         _qt_internal_execute_xcrun(sdk_path
             XCRUN_ARGS --sdk ${sdk_name} --show-sdk-path
@@ -933,7 +935,10 @@
 
 function(_qt_internal_get_apple_sdk_version out_var)
     set(sdk_version "")
-    if(APPLE)
+    if(APPLE AND IS_ABSOLUTE "${CMAKE_OSX_SYSROOT}" AND IS_DIRECTORY "${CMAKE_OSX_SYSROOT}")
+        file(READ "${CMAKE_OSX_SYSROOT}/SDKSettings.json" sdk_settings)
+        string(JSON sdk_version GET "${sdk_settings}" Version)
+    elseif(APPLE)
         _qt_internal_get_apple_sdk_name(sdk_name)
         _qt_internal_execute_xcrun(sdk_version
             XCRUN_ARGS --sdk ${sdk_name} --show-sdk-version
@@ -952,7 +957,7 @@
 
 function(_qt_internal_get_xcode_version_raw out_var)
     set(xcode_version "")
-    if(APPLE)
+    if(APPLE AND NOT QT_NO_XCODE_MIN_VERSION_CHECK)
         _qt_internal_execute_xcrun(xcode_version
             XCRUN_ARGS xcodebuild -version
             OUT_ERROR_VAR xcrun_error
