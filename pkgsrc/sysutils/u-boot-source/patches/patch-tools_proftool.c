$NetBSD$

--- a/tools/proftool.c
+++ b/tools/proftool.c
@@ -37,7 +37,7 @@
 
 /* from linux/kernel.h */
 #define __ALIGN_MASK(x, mask)	(((x) + (mask)) & ~(mask))
-#define ALIGN(x, a)		__ALIGN_MASK((x), (typeof(x))(a) - 1)
+#define PROF_ALIGN(x, a)		__ALIGN_MASK((x), (typeof(x))(a) - 1)
 
 /**
  * container_of - cast a member of a structure out to the containing structure
@@ -820,7 +820,7 @@
 	if (tw->str_ptr > abuf_size(&tw->str_buf)) {
 		int new_size;
 
-		new_size = ALIGN(tw->str_ptr, 4096);
+		new_size = PROF_ALIGN(tw->str_ptr, 4096);
 		if (!abuf_realloc(&tw->str_buf, new_size))
 			return -1;
 	}
@@ -953,7 +953,7 @@
 	int ret;
 
 	/* move to start of next page */
-	start = ALIGN(tw->ptr, TRACE_PAGE_SIZE);
+	start = PROF_ALIGN(tw->ptr, TRACE_PAGE_SIZE);
 	ret = fseek(tw->fout, start, SEEK_SET);
 	if (ret < 0) {
 		fprintf(stderr, "Cannot seek to page start\n");
@@ -986,7 +986,7 @@
 	ret = pop_len(tw, "page");
 	if (ret < 0)
 		return ret;
-	end = ALIGN(tw->ptr, TRACE_PAGE_SIZE);
+	end = PROF_ALIGN(tw->ptr, TRACE_PAGE_SIZE);
 
 	/*
 	 * Write a byte so that the data actually makes to the file, in the case
@@ -1532,7 +1532,7 @@
 	      start_ofs, len);
 
 	/* trace data */
-	start = ALIGN(start_ofs, TRACE_PAGE_SIZE);
+	start = PROF_ALIGN(start_ofs, TRACE_PAGE_SIZE);
 	tw->ptr += tputq(fout, start);
 
 	/* use a placeholder for the size */
