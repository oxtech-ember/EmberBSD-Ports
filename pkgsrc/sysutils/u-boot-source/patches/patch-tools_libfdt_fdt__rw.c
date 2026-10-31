$NetBSD$

--- a/tools/libfdt/fdt_rw.c
+++ b/tools/libfdt/fdt_rw.c
@@ -1,6 +1,6 @@
 // SPDX-License-Identifier: (GPL-2.0-or-later OR BSD-2-Clause)
 #include "fdt_host.h"
-#include "../../scripts/dtc/libfdt/fdt_rw.c"
+
 
 int fdt_remove_unused_strings(const void *old, void *new)
 {
@@ -11,7 +11,8 @@
 	const char *str;
 	int ret;
 	int tag = FDT_PROP;
-	int allocated;
+	char *strings;
+	int strings_size, len, i;
 
 	/* Make a copy and remove the strings */
 	memcpy(new, old, size);
@@ -26,9 +27,21 @@
 		new_prop = (struct fdt_property *)(unsigned long)
 			fdt_get_property_by_offset(new, offset, NULL);
 		str = fdt_string(old, fdt32_to_cpu(old_prop->nameoff));
-		ret = fdt_find_add_string_(new, str, strlen(str), &allocated);
-		if (ret < 0)
-			return ret;
+		strings = (char *)new + fdt_off_dt_strings(new);
+		strings_size = fdt_size_dt_strings(new);
+		len = strlen(str) + 1;
+		for (i = 0; i + len <= strings_size; i++) {
+			if (!memcmp(strings + i, str, len))
+				break;
+		}
+		if (i + len > strings_size) {
+			if (fdt_off_dt_strings(new) + strings_size + len > size)
+				return -FDT_ERR_NOSPACE;
+			memcpy(strings + strings_size, str, len);
+			fdt_set_size_dt_strings(new, strings_size + len);
+			i = strings_size;
+		}
+		ret = i;
 		new_prop->nameoff = cpu_to_fdt32(ret);
 	}
 
