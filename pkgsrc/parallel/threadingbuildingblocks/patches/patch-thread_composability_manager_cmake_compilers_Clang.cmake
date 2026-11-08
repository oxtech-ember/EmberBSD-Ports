$NetBSD$

Do not add the stack-clash flag on NetBSD.

--- thread_composability_manager/cmake/compilers/Clang.cmake.orig
+++ thread_composability_manager/cmake/compilers/Clang.cmake
@@ -17,7 +17,7 @@
 set(TCM_COMMON_COMPILE_FLAGS ${TCM_COMMON_COMPILE_FLAGS} $<$<NOT:$<CONFIG:Debug>>:-D_FORTIFY_SOURCE=2>
     -Wformat -Wformat-security -Werror=format-security -fPIC -fstack-protector-strong)
 
-if (NOT APPLE AND NOT ANDROID_PLATFORM AND CMAKE_SYSTEM_PROCESSOR MATCHES "(AMD64|amd64|i.86|x86)" AND NOT WIN32)
+if (NOT APPLE AND NOT ANDROID_PLATFORM AND CMAKE_SYSTEM_PROCESSOR MATCHES "(AMD64|amd64|i.86|x86)" AND NOT WIN32 AND NOT CMAKE_SYSTEM_NAME STREQUAL "NetBSD")
     set(TCM_LIB_COMPILE_FLAGS ${TCM_LIB_COMPILE_FLAGS} -fstack-clash-protection)
     if (NOT CF_PROTECTION_FULL_SUPPORTED)
         include(CheckCXXSourceCompiles)
