Keep comparator input const-correct for the selected compiler.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- gencode.c.orig
+++ gencode.c
@@ -5632,7 +5632,7 @@
 	 * the [int] return value on all architectures, so let's instead do it
 	 * in a way that is obviously correct.
 	 */
-	const uint32_t a32 = *((uint32_t *)a), b32 = *((uint32_t *)b);
+	const uint32_t a32 = *((const uint32_t *)a), b32 = *((const uint32_t *)b);
 	return a32 < b32 ? -1 :
 	    a32 > b32 ? 1 :
 	    0;
