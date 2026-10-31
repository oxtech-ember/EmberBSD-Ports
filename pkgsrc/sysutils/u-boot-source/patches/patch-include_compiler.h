$NetBSD$

--- a/include/compiler.h
+++ b/include/compiler.h
@@ -58,6 +58,26 @@
 # define __BYTE_ORDER BYTE_ORDER
 # define __LITTLE_ENDIAN LITTLE_ENDIAN
 # define __BIG_ENDIAN BIG_ENDIAN
+#elif defined(__NetBSD__)
+# include <sys/endian.h>
+# define __BYTE_ORDER _BYTE_ORDER
+# define __LITTLE_ENDIAN _LITTLE_ENDIAN
+# define __BIG_ENDIAN _BIG_ENDIAN
+#endif
+
+/* Compilers expose a portable byte-order triplet on other supported hosts. */
+#if !defined(__BYTE_ORDER) && defined(__BYTE_ORDER__) && \
+    defined(__ORDER_LITTLE_ENDIAN__) && defined(__ORDER_BIG_ENDIAN__)
+# define __BYTE_ORDER __BYTE_ORDER__
+# define __LITTLE_ENDIAN __ORDER_LITTLE_ENDIAN__
+# define __BIG_ENDIAN __ORDER_BIG_ENDIAN__
+#endif
+#if !defined(__BYTE_ORDER) || !defined(__LITTLE_ENDIAN) || \
+    !defined(__BIG_ENDIAN)
+# error "Host byte order is unknown"
+#endif
+#if __BYTE_ORDER != __LITTLE_ENDIAN && __BYTE_ORDER != __BIG_ENDIAN
+# error "Unsupported host byte order"
 #endif
 
 typedef uint8_t __u8;
