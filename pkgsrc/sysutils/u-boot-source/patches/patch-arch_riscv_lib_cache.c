$NetBSD$

--- a/arch/riscv/lib/cache.c
+++ b/arch/riscv/lib/cache.c
@@ -80,7 +80,7 @@
 		cbo_op(CBO_INVAL, start, end);
 }
 
-void invalidate_icache_all(void)
+__weak void invalidate_icache_all(void)
 {
 	asm volatile ("fence.i" ::: "memory");
 }
