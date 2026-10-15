$NetBSD$

Origin: EmberBSD (AI-assisted). Prefer the native Qt/kqueue backend on EmberBSD. The CM5
KDirWatch suite passes all 19 checks with QFSWatch; libinotify loses six
cases. Explicit backend choices remain available.
Propagate Qt watch-registration failures to the existing fallback selection.
An existing Qt watch remains successful. This also applies to
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
@@ -740,8 +746,12 @@
         connect(fsWatcher, &QFileSystemWatcher::directoryChanged, this, &KDirWatchPrivate::fswEventReceived);
         connect(fsWatcher, &QFileSystemWatcher::fileChanged, this, &KDirWatchPrivate::fswEventReceived);
     }
-    fsWatcher->addPath(e->path);
-    return true;
+    // Qt returns false for an existing watch as well as a registration error.
+    if (fsWatcher->files().contains(e->path) || fsWatcher->directories().contains(e->path)) {
+        return true;
+    }
+    // Let addWatch select its existing fallback when Qt cannot watch the path.
+    return fsWatcher->addPath(e->path);
 }
 #endif
 
