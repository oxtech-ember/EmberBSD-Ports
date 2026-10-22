Check the M4 search allocation and pass a pointer-typed null terminator to
the variadic filter constructor.

--- src/main.c.orig
+++ src/main.c
@@ -363,6 +363,10 @@
 
 					{
 						char *m4_path = calloc(endOfDir-path + 1 + m4_length + 1, 1);
+						if (!m4_path) {
+							flexerror(_("memory allocation failed while searching for GNU M4"));
+							return;
+						}
 
 						memcpy(m4_path, path, endOfDir-path);
 						m4_path[endOfDir-path] = '/';
@@ -381,7 +385,7 @@
 			}
 		}
 	}
-    filter_create_ext(output_chain, m4, "-P", 0);
+    filter_create_ext(output_chain, m4, "-P", (const char *)NULL);
     filter_create_int(output_chain, filter_fix_linedirs, NULL);
 
     /* For debugging, only run the requested number of filters. */
