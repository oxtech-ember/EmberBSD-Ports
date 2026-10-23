$NetBSD$

Bound LZO decoding by the allocated destination and require the declared size.
Reject decoded sizes that cannot fit the internal int allocation interface.
Origin: EmberBSD (AI-assisted). Not submitted upstream.
Uses the upstream LZO 2.10 safe API; no third-party patch was copied.

--- util/cairo-script/cairo-script-operators.c.orig
+++ util/cairo-script/cairo-script-operators.c
@@ -1755,6 +1755,10 @@
 {
     uint8_t *bytes;
 
+    /* Allocation helpers take int sizes, including the string terminator. */
+    if (src->deflate <= 0 || src->deflate >= INT_MAX)
+	return NULL;
+
     bytes = _csi_alloc (ctx, src->deflate + 1);
     if (bytes == NULL)
 	return NULL;
@@ -1777,9 +1781,10 @@
     {
 #if HAVE_LZO
         lzo_uint length = src->deflate;
-	if (lzo2a_decompress ((Bytef *) src->string, src->len,
+	if (lzo2a_decompress_safe ((Bytef *) src->string, src->len,
 			      (Bytef *) bytes, &length,
-			      NULL) == LZO_E_OK)
+			      NULL) == LZO_E_OK &&
+	    length == (lzo_uint) src->deflate)
 	{
             bytes[length] = '\0';
             return bytes;
@@ -3001,9 +3006,10 @@
         {
 #if HAVE_LZO
             lzo_uint out = s->deflate;
-	    if (lzo2a_decompress ((Bytef *) s->string, s->len,
+	    if (lzo2a_decompress_safe ((Bytef *) s->string, s->len,
 				  (Bytef *) data, &out,
-				  NULL))
+				  NULL) != LZO_E_OK ||
+		out != (lzo_uint) s->deflate)
 #endif
 		goto err_decompress;
 	    break;
