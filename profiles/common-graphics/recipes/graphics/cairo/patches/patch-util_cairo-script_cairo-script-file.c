$NetBSD$

Bound LZO decoding by the allocated destination and require the declared size.
Release the file object when its decoded string allocation fails.
Reject decoded sizes that cannot fit the internal int allocation interface.
Origin: EmberBSD (AI-assisted). Not submitted upstream.
Uses the upstream LZO 2.10 safe API; no third-party patch was copied.

--- util/cairo-script/cairo-script-file.c.orig
+++ util/cairo-script/cairo-script-file.c
@@ -154,6 +154,10 @@
 {
     csi_file_t *file;
 
+    /* Allocation helpers take int sizes, including the string terminator. */
+    if (src->deflate < 0 || src->deflate >= INT_MAX)
+	return _csi_error (CSI_STATUS_READ_ERROR);
+
     file = _csi_slab_alloc (ctx, sizeof (csi_file_t));
     if (_csi_unlikely (file == NULL))
 	return _csi_error (CAIRO_STATUS_NO_MEMORY);
@@ -167,8 +171,10 @@
 	csi_status_t status;
 
 	status = csi_string_new (ctx, &tmp_obj,  NULL, src->deflate);
-	if (_csi_unlikely (status))
+	if (_csi_unlikely (status)) {
+	    _csi_slab_free (ctx, file, sizeof (csi_file_t));
 	    return status;
+	}
 
 	tmp_str = tmp_obj.datum.string;
 	switch (src->method) {
@@ -191,9 +197,10 @@
         {
 #if HAVE_LZO
             lzo_uint len = src->deflate;
-	    if (lzo2a_decompress ((lzo_bytep) src->string, src->len,
+	    if (lzo2a_decompress_safe ((lzo_bytep) src->string, src->len,
 				  (lzo_bytep) tmp_str->string, &len,
-				  NULL))
+				  NULL) != LZO_E_OK ||
+		len != (lzo_uint) src->deflate)
 #endif
 		status = _csi_error (CAIRO_STATUS_NO_MEMORY);
 	    break;
