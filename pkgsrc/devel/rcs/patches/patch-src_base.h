# Origin: EmberBSD (AI-assisted).
Preserve the configured local Id keyword in the common RCS source.

--- src/base.h.orig
+++ src/base.h
@@ -314,14 +314,18 @@
 struct pool_found
 {
   int i;
-  struct tinysym const *sym;
+  char const *name;
 };
 
 #define TINY(x)       (tiny_ ## x)
 #define TINY_DECL(x)  const struct tinysym (TINY (x))
 
 /* Max length of the (working file) keywords.  */
+#ifdef LOCALID
+#define keylength 32
+#else
 #define keylength 8
+#endif
 
 /* This must be in the same order as in ‘keyword_pool’.  */
 enum markers
