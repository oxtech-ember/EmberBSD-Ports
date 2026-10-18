$NetBSD$

Use the real GCC instruction-cache builtin on NetBSD; retain errors elsewhere.
Origin: EmberBSD (AI-assisted), based on the pinned pkgsrc patch; not submitted upstream.

--- Source/JavaScriptCore/assembler/ARM64Assembler.h.orig
+++ Source/JavaScriptCore/assembler/ARM64Assembler.h
@@ -4041,6 +4041,8 @@
             linuxPageFlush(current, current + page);
 
         linuxPageFlush(current, end);
+#elif OS(NETBSD)
+        __builtin___clear_cache(static_cast<char*>(code), static_cast<char*>(code) + size);
 #elif OS(WINDOWS)
         FlushInstructionCache(GetCurrentProcess(), code, size);
 #else
