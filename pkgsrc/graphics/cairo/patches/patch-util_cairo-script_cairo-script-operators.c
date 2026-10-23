$NetBSD$

Bound LZO decoding by the allocated destination and require the declared size.
Reject decoded sizes that cannot fit the internal int allocation interface.
Release Cairo Script Interpreter source references when LZO decoding fails.
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
@@ -1829,11 +1834,19 @@
     /* no existing font_face, create new FT_Face */
     if (_ft_lib == NULL) {
 	err = FT_Init_FreeType (&_ft_lib);
-	if (_csi_unlikely (err != FT_Err_Ok))
+	if (_csi_unlikely (err != FT_Err_Ok)) {
+	    if (--source->base.ref == 0)
+		csi_string_free (ctx, source);
 	    return _csi_error (CSI_STATUS_NO_MEMORY);
+	}
     }
 
     data = _csi_slab_alloc (ctx, sizeof (*data));
+    if (_csi_unlikely (data == NULL)) {
+	if (--source->base.ref == 0)
+	    csi_string_free (ctx, source);
+	return _csi_error (CSI_STATUS_NO_MEMORY);
+    }
     data->bytes = NULL;
     data->source = source;
 
@@ -1843,8 +1856,12 @@
     if (source->deflate) {
 	len = source->deflate;
 	bytes = inflate_string (ctx, source);
-	if (_csi_unlikely (bytes == NULL))
+	if (_csi_unlikely (bytes == NULL)) {
+	    _csi_slab_free (ctx, data, sizeof (*data));
+	    if (--source->base.ref == 0)
+		csi_string_free (ctx, source);
 	    return _csi_error (CSI_STATUS_NO_MEMORY);
+	}
 
 	vec[1].bytes = bytes;
 	vec[1].num_bytes = len;
@@ -1938,8 +1955,11 @@
 
     if (string->deflate) {
 	bytes = inflate_string (ctx, string);
-	if (_csi_unlikely (bytes == NULL))
+	if (_csi_unlikely (bytes == NULL)) {
+	    if (--string->base.ref == 0)
+		csi_string_free (ctx, string);
 	    return _csi_error (CSI_STATUS_NO_MEMORY);
+	}
     } else {
 	bytes = tmpl.bytes;
     }
@@ -3001,9 +3021,10 @@
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
