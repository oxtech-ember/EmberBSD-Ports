$NetBSD$

Do not add the stack-clash flag on NetBSD, and leave link hardening to pkgsrc.

--- cmake/compilers/Clang.cmake.orig
+++ cmake/compilers/Clang.cmake
@@ -82,7 +82,7 @@
     $<$<NOT:$<PLATFORM_ID:Windows>>:-fPIC>
     $<$<NOT:$<PLATFORM_ID:Emscripten>>:-fstack-protector-strong>)
 
-if (NOT APPLE AND NOT ANDROID_PLATFORM AND CMAKE_SYSTEM_PROCESSOR MATCHES "(AMD64|amd64|i.86|x86)" AND NOT WIN32)
+if (NOT APPLE AND NOT ANDROID_PLATFORM AND CMAKE_SYSTEM_PROCESSOR MATCHES "(AMD64|amd64|i.86|x86)" AND NOT WIN32 AND NOT CMAKE_SYSTEM_NAME STREQUAL "NetBSD")
     set(TBB_LIB_COMPILE_FLAGS ${TBB_LIB_COMPILE_FLAGS} -fstack-clash-protection)
     if (NOT EMSCRIPTEN)
         # Some versions of Clang implicitly set -march=i686 when compiling for x86 and some don't.
@@ -102,11 +102,6 @@
     endif()
 endif()
 
-# -z switch is not supported on MacOS and Windows
-if (NOT APPLE AND NOT WIN32)
-    set(TBB_LIB_LINK_FLAGS ${TBB_LIB_LINK_FLAGS} -Wl,-z,relro,-z,now,-z,noexecstack)
-endif()
-
 set(TBB_COMMON_LINK_LIBS ${CMAKE_DL_LIBS})
 
 if (NOT CMAKE_CXX_FLAGS MATCHES "_FORTIFY_SOURCE")
