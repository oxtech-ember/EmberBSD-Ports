$NetBSD$

Origin: EmberBSD (AI-assisted); not submitted upstream.
Keep the output-name ownership flag only when leak cleanup uses it.

--- main.c.orig
+++ main.c
@@ -41,7 +41,9 @@
 char gflag;
 char iflag;
 char lflag;
+#ifdef NO_LEAKS
 static char oflag;
+#endif
 char rflag;
 char sflag;
 char tflag;
@@ -627,7 +629,9 @@
     /* if "-o filename" was not given */
     if (output_file_name == NULL)
     {
+#ifdef NO_LEAKS
 	oflag = 1;
+#endif
 	CREATE_FILE_NAME(output_file_name, OUTPUT_SUFFIX);
     }
 
