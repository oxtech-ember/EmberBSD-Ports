$NetBSD$

Refresh the existing pkgsrc platform adaptation for WebKitGTK 2.54.1.
Origin: EmberBSD (AI-assisted), based on the pinned pkgsrc patch; not submitted upstream.

--- Source/WebCore/loader/cache/CachedResource.h.orig
+++ Source/WebCore/loader/cache/CachedResource.h
@@ -46,6 +46,10 @@
 #include <wtf/WeakHashMap.h>
 #include <wtf/text/WTFString.h>
 
+#ifdef Status
+#undef Status
+#endif
+
 namespace WebCore {
 
 class CachedResourceCallback;
