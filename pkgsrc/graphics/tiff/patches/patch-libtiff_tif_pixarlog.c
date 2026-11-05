$NetBSD$

PDFium donor: fa4d5f8fbd89ea07273529daf9fd24fe1c7f6b9a
(Chromium Electron 45.2.1 DEPS, third_party/pdfium/third_party/libtiff).

Compare PixarLog buffer sizes without narrowing or signed overflow.
Adapt PDFium 0033-avail-out-overflow.patch without truncating 64-bit sizes.

--- libtiff/tif_pixarlog.c.orig
+++ libtiff/tif_pixarlog.c
@@ -943,7 +943,8 @@
         return (0);
     }
     /* Check that we will not fill more than what was allocated */
-    if ((tmsize_t)sp->stream.avail_out > sp->tbuf_size)
+    if (sp->tbuf_size < 0 ||
+        (uint64_t)sp->stream.avail_out > (uint64_t)sp->tbuf_size)
     {
         TIFFErrorExtR(tif, module, "sp->stream.avail_out > sp->tbuf_size");
         memset(op, 0, (size_t)occ);
