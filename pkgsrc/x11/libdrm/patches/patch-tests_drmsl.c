Origin: AI-assisted; upstream libdrm 2.4.134 tests/drmsl.c. Heap-allocate benchmark keys for standard process stack limits and handle allocation failures.

--- tests/drmsl.c.orig
+++ tests/drmsl.c
@@ -56,24 +56,46 @@
     }
 }
 
-static double do_time(int size, int iter)
+static int do_time(int size, int iter, double *usec_out)
 {
     void           *list;
     int            i, j;
-    unsigned long  keys[1000000];
+    unsigned long *keys;
     unsigned long  previous;
     unsigned long  key;
     void           *value;
     struct timeval start, stop;
-    double         usec;
     void           *ranstate;
 
+    keys = calloc((size_t)size, sizeof(*keys));
+    if (keys == NULL) {
+	fprintf(stderr, "Unable to allocate %d skip-list test keys\n", size);
+	return 0;
+    }
+
     list = drmSLCreate();
+    if (list == NULL) {
+	fprintf(stderr, "Unable to create skip list\n");
+	free(keys);
+	return 0;
+    }
     ranstate = drmRandomCreate(12345);
+    if (ranstate == NULL) {
+	fprintf(stderr, "Unable to create random state\n");
+	drmSLDestroy(list);
+	free(keys);
+	return 0;
+    }
 
     for (i = 0; i < size; i++) {
 	keys[i] = drmRandom(ranstate);
-	drmSLInsert(list, keys[i], NULL);
+	if (drmSLInsert(list, keys[i], NULL) < 0) {
+	    fprintf(stderr, "Unable to insert skip-list test key\n");
+	    drmRandomDestroy(ranstate);
+	    drmSLDestroy(list);
+	    free(keys);
+	    return 0;
+	}
     }
 
     previous = 0;
@@ -95,15 +117,16 @@
     }
     gettimeofday(&stop, NULL);
 
-    usec = (double)(stop.tv_sec * 1000000 + stop.tv_usec
+    *usec_out = (double)(stop.tv_sec * 1000000 + stop.tv_usec
 		    - start.tv_sec * 1000000 - start.tv_usec) / (size * iter);
 
-    printf("%0.2f microseconds for list length %d\n", usec, size);
-
-    drmRandomDouble(ranstate);
+    printf("%0.2f microseconds for list length %d\n", *usec_out, size);
+
+    drmRandomDestroy(ranstate);
     drmSLDestroy(list);
-
-    return usec;
+    free(keys);
+
+    return 1;
 }
 
 static void print_neighbors(void *list, unsigned long key,
@@ -139,14 +162,22 @@
     double   usec, usec2, usec3, usec4;
 
     list = drmSLCreate();
+    if (list == NULL) {
+	fprintf(stderr, "Unable to create skip list\n");
+	return EXIT_FAILURE;
+    }
     printf( "list at %p\n", list);
 
     print(list);
     printf("\n==============================\n\n");
 
-    drmSLInsert(list, 123, NULL);
-    drmSLInsert(list, 213, NULL);
-    drmSLInsert(list, 50, NULL);
+    if (drmSLInsert(list, 123, NULL) < 0 ||
+	drmSLInsert(list, 213, NULL) < 0 ||
+	drmSLInsert(list, 50, NULL) < 0) {
+	fprintf(stderr, "Unable to insert skip-list test key\n");
+	drmSLDestroy(list);
+	return EXIT_FAILURE;
+    }
     print(list);
     printf("\n==============================\n\n");
 
@@ -167,16 +198,20 @@
     drmSLDestroy(list);
     printf("\n==============================\n\n");
 
-    usec  = do_time(100, 10000);
-    usec2 = do_time(1000, 500);
+    if (!do_time(100, 10000, &usec))
+	return EXIT_FAILURE;
+    if (!do_time(1000, 500, &usec2))
+	return EXIT_FAILURE;
     printf("Table size increased by %0.2f, search time increased by %0.2f\n",
 	   1000.0/100.0, usec2 / usec);
 
-    usec3 = do_time(10000, 50);
+    if (!do_time(10000, 50, &usec3))
+	return EXIT_FAILURE;
     printf("Table size increased by %0.2f, search time increased by %0.2f\n",
 	   10000.0/100.0, usec3 / usec);
 
-    usec4 = do_time(100000, 4);
+    if (!do_time(100000, 4, &usec4))
+	return EXIT_FAILURE;
     printf("Table size increased by %0.2f, search time increased by %0.2f\n",
 	   100000.0/100.0, usec4 / usec);
 
