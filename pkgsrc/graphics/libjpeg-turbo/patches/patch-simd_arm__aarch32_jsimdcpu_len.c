$NetBSD$

Initialize the NetBSD sysctl output length (EmberBSD, AI-assisted).

--- simd/arm/aarch32/jsimdcpu.c.orig
+++ simd/arm/aarch32/jsimdcpu.c
@@ -113,7 +113,7 @@
   int bufsize = 1024; /* an initial guess for the line buffer size limit */
 #elif defined(__NetBSD__)
   int neon_present;
-  size_t len;
+  size_t len = sizeof(neon_present);
 #endif
 #endif
   unsigned int simd_support = 0;
