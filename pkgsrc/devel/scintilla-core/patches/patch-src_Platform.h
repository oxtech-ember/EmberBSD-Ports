$NetBSD$

Expose an explicit toolkit-free build selection without defaulting to Win32.
Origin: EmberBSD contributors (AI-assisted).

--- src/Platform.h.orig
+++ src/Platform.h
@@ -28,7 +28,9 @@
 #define PLAT_TK 0
 #define PLAT_HAIKU 0
 
-#if defined(FOX)
+#if defined(SCINTILLA_CORE)
+// The shared editing archive has no widget backend. Frontends implement this API.
+#elif defined(FOX)
 #undef PLAT_FOX
 #define PLAT_FOX 1
 
