$NetBSD$

Refresh the existing pkgsrc platform adaptation for WebKitGTK 2.54.1.
Origin: EmberBSD (AI-assisted), based on the pinned pkgsrc patch; not submitted upstream.

--- Source/cmake/WebKitFeatures.cmake.orig
+++ Source/cmake/WebKitFeatures.cmake
@@ -89,7 +89,7 @@
             set(ENABLE_C_LOOP_DEFAULT ON)
             set(ENABLE_SAMPLING_PROFILER_DEFAULT OFF)
         endif ()
-    elseif (WTF_CPU_ARM64 OR WTF_CPU_X86_64)
+    elseif (WTF_OS_LINUX AND (WTF_CPU_ARM64 OR WTF_CPU_X86_64))
         set(ENABLE_JIT_DEFAULT ON)
         set(ENABLE_FTL_DEFAULT ON)
         set(USE_SYSTEM_MALLOC_DEFAULT OFF)
@@ -110,7 +110,7 @@
         set(USE_MIMALLOC_DEFAULT ON)
         set(ENABLE_C_LOOP_DEFAULT ON)
         set(ENABLE_SAMPLING_PROFILER_DEFAULT OFF)
-    elseif (WTF_CPU_RISCV64)
+    elseif (WTF_CPU_RISCV64 AND WTF_OS_LINUX)
         set(ENABLE_JIT_DEFAULT ON)
         set(ENABLE_FTL_DEFAULT ON)
         set(USE_SYSTEM_MALLOC_DEFAULT OFF)
