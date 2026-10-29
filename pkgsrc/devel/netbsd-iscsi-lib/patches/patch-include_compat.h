Use expression-valued portable byte-order conversion for ordinary builds.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- include/compat.h.orig
+++ include/compat.h
@@ -51,13 +51,22 @@
 #  define ISCSI_BE64TOH(x)	be64toh(x)
 #else
 #  if defined(HAVE_LIBKERN_OSBYTEORDER_H)
-#    define ISCSI_HTOBE64(x)	(x) = OSSwapBigToHostInt64((u_int64_t)(x))
-#  elif _BYTE_ORDER == _BIG_ENDIAN
+#    define ISCSI_HTOBE64(x)	OSSwapBigToHostInt64((u_int64_t)(x))
+#  elif defined(_BYTE_ORDER) && defined(_BIG_ENDIAN) && _BYTE_ORDER == _BIG_ENDIAN
 #    define ISCSI_HTOBE64(x)	(x)
-#  elif defined(HAVE___BSWAP64)
-#    define ISCSI_HTOBE64(x)	(x) = __bswap64((u_int64_t)(x))
 #  else   /* LITTLE_ENDIAN */
-#    define ISCSI_HTOBE64(x)	(((uint64_t)(ISCSI_NTOHL((uint32_t)(((x) << 32) >> 32))) << 32) | (uint32_t)ISCSI_NTOHL(((uint32_t)((x) >> 32))))
+static inline uint64_t
+iscsi_htobe64(uint64_t value)
+{
+	uint64_t result;
+	uint8_t *bytes = (uint8_t *)&result;
+	unsigned int i;
+
+	for (i = 0; i < sizeof(result); i++)
+		bytes[i] = (uint8_t)(value >> (56 - 8 * i));
+	return result;
+}
+#    define ISCSI_HTOBE64(x)	iscsi_htobe64(x)
 #  endif  /* LITTLE_ENDIAN */
 #  define ISCSI_BE64TOH(x)	ISCSI_HTOBE64(x)
 #endif
