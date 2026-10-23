$NetBSD$

Origin: EmberBSD (AI-assisted). Preserve compiler fallback when stderr is closed.
Initialize and resolve original arguments before fallible stderr setup.
The fallback never returns on POSIX or Windows; describe that existing contract.

--- CCache/ccache.c.orig
+++ CCache/ccache.c
@@ -99,6 +99,10 @@
 /*
   something went badly wrong - just execute the real compiler
 */
+#if defined(__GNUC__)
+static void failed(void) __attribute__((__noreturn__));
+#endif
+
 static void failed(void)
 {
 	char *e;
@@ -1166,11 +1170,16 @@
 }
 
 /* the main ccache driver function */
+static void setup_uncached_err(void);
+
 static void ccache(int argc, char *argv[])
 {
 	/* find the real compiler */
 	find_compiler(argc, argv);
 
+	/* Error fallback requires initialized original compiler arguments. */
+	setup_uncached_err();
+
 	/* use the real compiler if HOME is not set */
 	if (!cache_dir) {
 		cc_log("Unable to determine home directory\n");
@@ -1366,7 +1375,6 @@
 		ccache_verbose = 1;
 	}
 
-	setup_uncached_err();
 	
 
 	/* the user might have set CCACHE_UMASK */
