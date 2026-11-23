$NetBSD$

Origin: EmberBSD (AI-assisted), local, not submitted upstream.
The Linux error dialog helper is not built on NetBSD. Write the second
instance message to stderr.

--- src/Utilities/Platform/Platform.cc.orig
+++ src/Utilities/Platform/Platform.cc
@@ -279,8 +279,10 @@ int Platform::showMultipleInstanceError([[maybe_unused]] int argc, [[maybe_unuse
     // MessageBoxW is GUI-only; also write to stderr so a CLI/headless launch sees the reason.
     fprintf(stderr, "Error: %s\n", message.toLocal8Bit().constData());
     MessageBoxW(nullptr, message.toStdWString().c_str(), L"Error", MB_OK | MB_ICONERROR);
-#else
+#elif (defined(Q_OS_LINUX) || defined(Q_OS_FREEBSD))
     showLinuxErrorDialog(message.toLocal8Bit());
+#else
+    fprintf(stderr, "Error: %s\n", message.toLocal8Bit().constData());
 #endif
     return -1;
 }
