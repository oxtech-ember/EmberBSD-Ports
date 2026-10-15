$NetBSD: patch-src_powerpc_ffi__powerpc.h,v 1.2 2021/12/08 08:20:17 adam Exp $

Workaround for ILP32 powerpc, which doesn't have 128-bit-length data types.

Rebase: EmberBSD (AI-assisted), for libffi 3.8.0.
Preserve both ILP32 guards around the float128 type and helper declaration.

--- src/powerpc/ffi_powerpc.h.orig
+++ src/powerpc/ffi_powerpc.h
@@ -124,6 +124,7 @@
   double d;
 } ffi_dblfl;
 
+#ifdef POWERPC64
 #if defined(__FLOAT128_TYPE__) && defined(__HAVE_FLOAT128)
 typedef _Float128 float128;
 #elif defined(__FLOAT128__)
@@ -131,6 +132,7 @@
 #else
 typedef char float128[16] __attribute__((aligned(16)));
 #endif
+#endif /* POWERPC64 */
 
 void FFI_HIDDEN ffi_closure_SYSV (void);
 void FFI_HIDDEN ffi_go_closure_sysv (void);
@@ -164,11 +166,13 @@
 						    void (*) (ffi_cif *, void *,
 							      void **, void *),
 						    void *, void *);
+#ifdef POWERPC64
 int FFI_HIDDEN ffi_closure_helper_LINUX64 (ffi_cif *,
 					   void (*) (ffi_cif *, void *,
 						     void **, void *),
 					   void *, void *,
 					   unsigned long *, ffi_dblfl *,
 					   float128 *);
+#endif
 
 #endif /* !LIBFFI_ASM */
