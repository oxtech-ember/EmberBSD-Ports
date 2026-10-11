$NetBSD$

Origin: EmberBSD (AI-assisted). Prefer the native Qt/kqueue backend on EmberBSD. The CM5
KDirWatch suite passes all 19 checks with QFSWatch; libinotify loses six
cases. Explicit backend choices remain available. This also applies to
compatible NetBSD builds using the same recipe.

--- src/lib/io/kdirwatch.cpp.orig
+++ src/lib/io/kdirwatch.cpp
@@ -95,6 +95,12 @@
 // Convert a string into a watch Method
 static KDirWatch::Method methodFromString(const QByteArray &method)
 {
+#if defined(Q_OS_NETBSD) && HAVE_QFILESYSTEMWATCHER
+    // Qt uses native kqueue; libinotify currently loses file change events.
+    if (method == "default") {
+        return KDirWatch::QFSWatch;
+    }
+#endif
     if (method == "Stat") {
         return KDirWatch::Stat;
     } else if (method == "QFSWatch") {
