$NetBSD$

EmberBSD: tell the preprocessor that the input is C. Clang and GCC
compiler drivers, which are the usual "cpp" on Darwin and in cross
builds, treat .x files as linker input and write empty output.

--- rpcgen/rpc_main.c.orig
+++ rpcgen/rpc_main.c
@@ -367,6 +367,9 @@
       find_cpp ();
       putarg (0, CPP);
       putarg (1, CPPFLAGS);
+      /* Compiler drivers treat .x files as linker input. */
+      addarg ("-x");
+      addarg ("c");
       addarg (define);
       if (infile)
 	addarg (infile);
