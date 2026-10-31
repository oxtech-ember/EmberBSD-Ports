$NetBSD$

--- a/include/cpu_func.h
+++ b/include/cpu_func.h
@@ -68,6 +68,7 @@
 void flush_dcache_range(unsigned long start, unsigned long stop);
 void invalidate_dcache_range(unsigned long start, unsigned long stop);
 void invalidate_dcache_all(void);
+void invalidate_icache_range(unsigned long start, unsigned long stop);
 void invalidate_icache_all(void);
 
 enum pgprot_attrs {
