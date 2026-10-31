$NetBSD$

Bound memory-mapped NOR reads when the platform supplies a range.

--- a/common/spl/spl_nor.c
+++ b/common/spl/spl_nor.c
@@ -10,11 +10,25 @@
 #include <spl.h>
 #include <spl_load.h>
 
+/* Boards may constrain reads to a memory-mapped NOR aperture. */
+bool __weak spl_nor_get_bounds(ulong *start, ulong *size)
+{
+	return false;
+}
+
 static ulong spl_nor_load_read(struct spl_load_info *load, ulong sector,
 			       ulong count, void *buf)
 {
+	ulong start, size;
+
 	debug("%s: sector %lx, count %lx, buf %p\n",
 	      __func__, sector, count, buf);
+	if (!count || count - 1 > ~0UL - sector)
+		return 0;
+	if (spl_nor_get_bounds(&start, &size) &&
+	    (sector < start || sector - start > size ||
+	     count > size - (sector - start)))
+		return 0;
 	memcpy(buf, map_sysmem(sector, count), count);
 
 	return count;
