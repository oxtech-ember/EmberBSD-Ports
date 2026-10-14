$NetBSD$

Treat NetBSD like the other BSD platforms in the vendored RenderDoc API
header. Origin: EmberBSD (AI-assisted).

--- src/third_party/renderdoc/renderdoc_app.h	2026-09-15 17:26:39.000000000 +0300
+++ src/third_party/renderdoc/renderdoc_app.h	2026-10-14 11:19:47.827825076 +0300
@@ -35,7 +35,7 @@
 
 #if defined(WIN32) || defined(__WIN32__) || defined(_WIN32) || defined(_MSC_VER)
 #define RENDERDOC_CC __cdecl
-#elif defined(__linux__) || defined(__FreeBSD__)
+#elif defined(__linux__) || defined(__FreeBSD__) || defined(__NetBSD__)
 #define RENDERDOC_CC
 #elif defined(__APPLE__)
 #define RENDERDOC_CC
