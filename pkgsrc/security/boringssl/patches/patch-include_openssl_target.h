$NetBSD$

Origin: pkgsrc www/chromium NetBSD patches, based on OpenBSD chromium
and pkgsrc qt5-qtwebengine patches; adapted by EmberBSD.

diff --git include/openssl/target.h include/openssl/target.h
index 2372a05..e5d2bb7 100644
--- include/openssl/target.h
+++ include/openssl/target.h
@@ -187,6 +187,10 @@
 #define OPENSSL_OPENBSD
 #endif
 
+#if defined(__NetBSD__)
+#define OPENSSL_NETBSD
+#endif
+
 // BoringSSL requires platform's locking APIs to make internal global state
 // thread-safe, including the PRNG. On some single-threaded embedded platforms,
 // locking APIs may not exist, so this dependency may be disabled with the
