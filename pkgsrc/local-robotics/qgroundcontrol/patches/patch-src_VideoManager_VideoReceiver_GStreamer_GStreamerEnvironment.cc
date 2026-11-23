$NetBSD$

Origin: EmberBSD (AI-assisted), local, not submitted upstream.
Build the bundled GStreamer path helpers only on the platforms that use
them. NetBSD uses the installed GStreamer and its default plugin path.

--- src/VideoManager/VideoReceiver/GStreamer/GStreamerEnvironment.cc.orig
+++ src/VideoManager/VideoReceiver/GStreamer/GStreamerEnvironment.cc
@@ -49,10 +49,13 @@ void _resetEnvValidation()
     s_envPathsValid = true;
 }
 
+#if defined(Q_OS_MACOS) || defined(Q_OS_WIN) || defined(Q_OS_IOS) || defined(Q_OS_ANDROID) || \
+    defined(Q_OS_LINUX)
 QString _cleanJoin(const QString& base, const QString& relative)
 {
     return QDir::cleanPath(QDir(base).filePath(relative));
 }
+#endif
 
 void _setGstEnv(const char* name, const QString& value)
 {
@@ -150,7 +153,8 @@ bool _extractApkAsset(const char* assetPath, const QString& destPath)
 }
 #endif
 
-#if !defined(Q_OS_ANDROID) && !defined(Q_OS_IOS)
+#if !defined(Q_OS_ANDROID) && !defined(Q_OS_IOS) && \
+    (defined(Q_OS_MACOS) || defined(Q_OS_WIN) || defined(Q_OS_LINUX))
 
 // Caller must hold s_setEnvVarsMutex.
 void _setEnvValidationError(const QString& error)
@@ -181,6 +185,7 @@ bool _isExecutableFile(const QString& path)
     return fileInfo.exists() && fileInfo.isFile() && fileInfo.isExecutable();
 }
 
+#if defined(Q_OS_MACOS) || defined(Q_OS_LINUX)
 QString _firstExistingPath(const QStringList& paths)
 {
     for (const QString& path : paths) {
@@ -191,6 +196,7 @@ QString _firstExistingPath(const QStringList& paths)
 
     return {};
 }
+#endif
 
 #if defined(Q_OS_MACOS)
 QString _joinExistingPaths(const QStringList& paths)
@@ -340,7 +346,7 @@ bool _validateBundledDesktopPaths(const QString& platformLabel, const QString& p
     return true;
 }
 
-#endif  // !Q_OS_ANDROID && !Q_OS_IOS
+#endif
 
 void _setGstEnvVars()
 {
