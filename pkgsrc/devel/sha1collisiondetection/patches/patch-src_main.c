$NetBSD$

Bring the release command to upstream a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988.
https://github.com/cr-marcstevens/sha1collisiondetection/compare/stable-v1.0.3...a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988

--- src/main.c.orig
+++ src/main.c
@@ -8,9 +8,32 @@
 #include <stdio.h>
 #include <stdlib.h>
 #include <string.h>
+#include <errno.h>
+#ifndef _WIN32
 #include <libgen.h>
+#endif
 
 #include "sha1.h"
+
+#ifdef _WIN32
+char* basename(char* path)
+{
+    char *base = NULL, *cur = NULL;
+
+    base = path;
+    cur = path;
+    while (0 != *cur)
+    {
+        if ('\\' == *cur)
+        {
+            base = cur + 1;
+        }
+        cur++;
+    }
+
+    return base;
+}
+#endif
 
 int main(int argc, char** argv)
 {
@@ -23,7 +46,7 @@
 
 	if (argc < 2)
 	{
-		printf("Usage: %s <file>\n", basename(argv[0]));
+		fprintf(stderr, "Usage: %s <file>\n", basename(argv[0]));
 		return 1;
 	}
 
@@ -37,10 +60,14 @@
 			SHA1DCSetDetectReducedRoundCollision(&ctx2, 1);
 		}
 
-		fd = fopen(argv[i], "rb");
+		if(!strcmp(argv[i],"-")) {
+			fd = stdin;
+		} else {
+			fd = fopen(argv[i], "rb");
+		}
 		if (fd == NULL)
 		{
-			printf("cannot open file: %s\n", argv[i]);
+			fprintf(stderr, "cannot open file: %s: %s\n", argv[i], strerror(errno));
 			return 1;
 		}
 
@@ -53,12 +80,12 @@
 		}
 		if (ferror(fd))
 		{
-			printf("error while reading file: %s\n", argv[i]);
+			fprintf(stderr, "error while reading file: %s: %s\n", argv[i], strerror(errno));
 			return 1;
 		}
 		if (!feof(fd))
 		{
-			printf("not end of file?: %s\n",argv[i]);
+			fprintf(stderr, "not end of file?: %s: %s\n", argv[i], strerror(errno));
 			return 1;
 		}
 
@@ -82,3 +109,7 @@
 	}
 	return 0;
 }
+
+#ifdef _MSC_VER
+#pragma warning(disable : 4710 )    /* 4710 -- compiler complains about printf,sprintf not being inlined. */
+#endif
