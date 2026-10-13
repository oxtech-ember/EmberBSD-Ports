Release the file array when main reaches its final exit.
This host-provider patch covers normal main completion, including an input
error reported through ok. It does not cover earlier fatal exits or inotify
exit paths. File names borrow argv/gettext storage and remain untouched.
Upstream: GNU coreutils 9.12, src/tail.c, GPL-3.0-or-later.
Origin: EmberBSD, AI-assisted; not submitted upstream.

--- src/tail.c.orig
+++ src/tail.c
@@ -2531,5 +2531,6 @@
 
   if (have_read_stdin && close (STDIN_FILENO) < 0)
     error (EXIT_FAILURE, errno, "-");
+  free (F);
   main_exit (ok ? EXIT_SUCCESS : EXIT_FAILURE);
 }
