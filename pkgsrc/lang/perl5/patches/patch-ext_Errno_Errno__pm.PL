$NetBSD$

Origin: EmberBSD (AI-assisted), not submitted upstream.
Preprocess nested errno headers with their public entry header first.
Private sys/cdefs_elf.h needs definitions from sys/cdefs.h; errors were ignored
and could silently omit constants. A failing compiler now fails generation.

--- ext/Errno/Errno_pm.PL.orig
+++ ext/Errno/Errno_pm.PL
@@ -61,7 +61,7 @@
     }
     elsif ($Config{gccversion} ne '' && $^O ne 'darwin' && $^O ne 'os390') {
 	# With the -dM option, gcc outputs every #define it finds
-	unless(open(FH,"$Config{cc} -E -dM $Config{cppflags} $file |")) {
+	unless(open(FH,"$Config{cc} -E -dM $Config{cppflags} -include errno.h $file |")) {
             warn "Cannot open '$file'";
             return;
 	}     
@@ -86,7 +86,7 @@
 	    if /$pat/;
     }
 
-    close(FH);
+    close(FH) or die "Failed to read errno definitions from $file\n";
 }
 
 my $cppstdin;
