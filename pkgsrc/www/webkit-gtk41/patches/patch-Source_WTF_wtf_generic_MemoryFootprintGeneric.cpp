$NetBSD$

Use the generic fallback on platforms without memoryStatus().
Origin: EmberBSD (AI-assisted), for the pinned WebKitGTK 2.54.1 source.

--- Source/WTF/wtf/generic/MemoryFootprintGeneric.cpp.orig
+++ Source/WTF/wtf/generic/MemoryFootprintGeneric.cpp
@@ -33,8 +33,13 @@
 
 size_t memoryFootprint()
 {
+#if PLATFORM(IOS_FAMILY) || OS(LINUX) || OS(FREEBSD)
     auto memoryUse = memoryStatus();
     return memoryUse.memoryFootprint;
+#else
+    // Generic targets without memoryStatus() report no process footprint.
+    return 0;
+#endif
 }
 
 } // namespace WTF
