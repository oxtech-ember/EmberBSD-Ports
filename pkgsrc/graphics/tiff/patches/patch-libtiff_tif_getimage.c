$NetBSD$

PDFium donor: fa4d5f8fbd89ea07273529daf9fd24fe1c7f6b9a
(Chromium Electron 45.2.1 DEPS, third_party/pdfium/third_party/libtiff).

Bound strip dimensions as in PDFium 0031-safe_size_ingtStripContig.patch.
Use unsigned addition after the existing range validation to avoid signed overflow.

--- libtiff/tif_getimage.c.orig
+++ libtiff/tif_getimage.c
@@ -1163,6 +1163,11 @@
     int ret = 1, flip;
     tmsize_t maxstripsize;
 
+    /* TIFFRGBAImageGet has already validated the nonnegative row offset. */
+    if ((uint64_t)(uint32_t)img->row_offset > (uint64_t)TIFF_TMSIZE_T_MAX ||
+        (uint64_t)h > (uint64_t)TIFF_TMSIZE_T_MAX)
+        return 0;
+
     /* If the raster is smaller than the image,
      * or if there is a col_offset, adapt the samples to be copied per row. */
     uint32_t wmin;
@@ -1224,13 +1229,13 @@
     {
         uint32_t temp;
         rowstoread = rowsperstrip -
-                     (uint32_t)((int32_t)row + img->row_offset) % rowsperstrip;
+                     (row + (uint32_t)img->row_offset) % rowsperstrip;
         nrow = (row + rowstoread > h ? h - row : rowstoread);
         nrowsub = nrow;
         if ((nrowsub % subsamplingver) != 0)
             nrowsub += subsamplingver - nrowsub % subsamplingver;
         temp =
-            (uint32_t)((int32_t)row + img->row_offset) % rowsperstrip + nrowsub;
+            (row + (uint32_t)img->row_offset) % rowsperstrip + nrowsub;
         if (scanline > 0 && temp > (size_t)(TIFF_TMSIZE_T_MAX / scanline))
         {
             TIFFErrorExtR(tif, TIFFFileName(tif),
@@ -1240,7 +1245,7 @@
         if (_TIFFReadEncodedStripAndAllocBuffer(
                 tif,
                 TIFFComputeStrip(tif,
-                                 (uint32_t)((int32_t)row + img->row_offset), 0),
+                                 (row + (uint32_t)img->row_offset), 0),
                 (void **)(&buf), maxstripsize,
                 (tmsize_t)((size_t)temp * (size_t)scanline)) ==
                 (tmsize_t)(-1) &&
@@ -1250,7 +1255,7 @@
             break;
         }
 
-        pos = (tmsize_t)((uint32_t)((int32_t)row + img->row_offset) %
+        pos = (tmsize_t)((row + (uint32_t)img->row_offset) %
                          rowsperstrip) *
                   scanline +
               ((tmsize_t)img->col_offset * img->samplesperpixel);
