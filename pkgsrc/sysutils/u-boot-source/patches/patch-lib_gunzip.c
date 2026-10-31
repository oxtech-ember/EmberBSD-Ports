$NetBSD$

--- a/lib/gunzip.c
+++ b/lib/gunzip.c
@@ -28,23 +28,6 @@
 #define COMMENT			0x10
 #define RESERVED		0xe0
 #define DEFLATED		8
-
-void *gzalloc(void *x, unsigned items, unsigned size)
-{
-	void *p;
-
-	size *= items;
-	size = (size + ZALLOC_ALIGNMENT - 1) & ~(ZALLOC_ALIGNMENT - 1);
-
-	p = malloc (size);
-
-	return (p);
-}
-
-void gzfree(void *x, void *addr, unsigned nb)
-{
-	free (addr);
-}
 
 __rcode int gzip_parse_header(const unsigned char *src, unsigned long len)
 {
@@ -210,6 +193,7 @@
 
 	s.zalloc = gzalloc;
 	s.zfree = gzfree;
+	s.opaque = Z_NULL;
 
 	r = inflateInit2(&s, -MAX_WBITS);
 	if (r != Z_OK) {
@@ -326,6 +310,7 @@
 
 	s.zalloc = gzalloc;
 	s.zfree = gzfree;
+	s.opaque = Z_NULL;
 
 	r = inflateInit2(&s, -MAX_WBITS);
 	if (r != Z_OK) {
