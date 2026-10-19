$NetBSD$

Origin: EmberBSD (AI-assisted). Prefer the native Qt/kqueue backend on EmberBSD. The CM5
KDirWatch suite passes all 19 checks with QFSWatch; libinotify loses six
cases. Explicit backend choices remain available.
Propagate Qt watch-registration failures to the existing fallback selection.
An existing Qt watch remains successful. This also applies to
compatible NetBSD builds using the same recipe.

Use at most half the finite soft descriptor limit for unique Qt paths.
Keep the remaining entries on the existing Stat backend. This is a per-watcher
budget, not a process-wide descriptor reserve. Re-registration uses the same
policy. Keep polling entries stable to preserve their timer accounting.

Snapshot child paths before recursive Qt events. Scanning a child can remove
it from its parent's list and delete an unowned parent. Look up each path
again during recursion. Re-register files only while they exist; repeated
missing-file events must not append duplicate parent dependencies.

--- src/lib/io/kdirwatch.cpp.orig
+++ src/lib/io/kdirwatch.cpp
@@ -48,6 +48,9 @@
 #include <assert.h>
 #include <cerrno>
 #include <sys/stat.h>
+#if defined(Q_OS_NETBSD)
+#include <sys/resource.h>
+#endif
 
 #include <qplatformdefs.h> // QT_LSTAT, QT_STAT, QT_STATBUF
 
@@ -95,6 +98,12 @@
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
@@ -718,6 +727,12 @@
 #if HAVE_QFILESYSTEMWATCHER
 bool KDirWatchPrivate::useQFSWatch(Entry *e)
 {
+#if defined(Q_OS_NETBSD)
+    // Keep polling entries stable when an inode changes or a queued Qt event arrives.
+    if (e->m_mode == StatMode) {
+        return useStat(e);
+    }
+#endif
     e->m_mode = QFSWatchMode;
     e->dirty = false;
 
@@ -734,14 +749,34 @@
         return true;
     }
 
-    // qCDebug(KDIRWATCH) << "fsWatcher->addPath" << e->path;
+    // Qt returns false for an existing watch as well as a registration error.
+    if (fsWatcher && (fsWatcher->files().contains(e->path) || fsWatcher->directories().contains(e->path))) {
+        return true;
+    }
+#if defined(Q_OS_NETBSD)
+    // kqueue holds one descriptor per path. Bound this shared watcher's share.
+    struct rlimit limit;
+    if (getrlimit(RLIMIT_NOFILE, &limit) != 0) {
+        qCWarning(KDIRWATCH) << "Cannot read the descriptor limit; polling" << e->path << strerror(errno);
+        return useStat(e);
+    }
+    if (limit.rlim_cur == RLIM_INFINITY || limit.rlim_cur < 2) {
+        qCWarning(KDIRWATCH) << "No finite Qt watch budget; polling" << e->path;
+        return useStat(e);
+    }
+    const rlim_t watched = fsWatcher ? rlim_t(fsWatcher->files().size()) + rlim_t(fsWatcher->directories().size()) : 0;
+    if (watched >= limit.rlim_cur / 2) {
+        qCDebug(KDIRWATCH) << "Qt watch budget reached; polling" << e->path;
+        return useStat(e);
+    }
+#endif
     if (!fsWatcher) {
         fsWatcher = new QFileSystemWatcher();
         connect(fsWatcher, &QFileSystemWatcher::directoryChanged, this, &KDirWatchPrivate::fswEventReceived);
         connect(fsWatcher, &QFileSystemWatcher::fileChanged, this, &KDirWatchPrivate::fswEventReceived);
     }
-    fsWatcher->addPath(e->path);
-    return true;
+    // Let addWatch select its existing fallback when Qt cannot watch the path.
+    return fsWatcher->addPath(e->path);
 }
 #endif
 
@@ -1648,17 +1683,28 @@
             addWatch(entry);
         } else if (entry->isDir) {
             // Check if any file or dir was created under this directory, that we were waiting for
-            for (Entry *sub_entry : std::as_const(entry->m_entries)) {
-                fswEventReceived(sub_entry->path); // recurse, to call scanEntry and see if something changed
-            }
-        } else {
+            // Scanning a child can remove it from this list and delete the parent entry.
+            QStringList subEntryPaths;
+            subEntryPaths.reserve(entry->m_entries.size());
+            for (const Entry *sub_entry : std::as_const(entry->m_entries)) {
+                subEntryPaths.append(sub_entry->path);
+            }
+            for (const QString &subEntryPath : std::as_const(subEntryPaths)) {
+                fswEventReceived(subEntryPath); // look up each child again after earlier scans
+            }
+        } else if (entry->m_status == Normal) {
             /* Even though QFileSystemWatcher only reported the file as modified, it is possible that the file
              * was in fact just deleted and then immediately recreated.  If the file was deleted, QFileSystemWatcher
              * will delete the watch, and will ignore the file, even after it is recreated.  Since it is impossible
              * to reliably detect this case, always re-request the watch on a dirty signal, to avoid losing the
              * underlying OS monitor.
              */
+#if defined(Q_OS_NETBSD)
+            // Re-registration must use the same budget and error fallback.
+            addWatch(entry);
+#else
             fsWatcher->addPath(entry->path);
+#endif
         }
     }
 }
