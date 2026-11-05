$NetBSD$

PDFium donor: fa4d5f8fbd89ea07273529daf9fd24fe1c7f6b9a
(Chromium Electron 45.2.1 DEPS, third_party/pdfium/third_party/libtiff).

Reject excessive strip and tile counts before directory allocation.
Adapt PDFium 0028-nstrips-OOM.patch to per-handle error reporting.

--- libtiff/tif_dirread.c.orig
+++ libtiff/tif_dirread.c
@@ -4992,6 +4992,13 @@
                       isTiled(tif) ? "tiles" : "strips");
         goto bad;
     }
+    if (tif->tif_dir.td_nstrips > INT_MAX)
+    {
+        TIFFErrorExtR(tif, module, "Cannot handle %u number of %s",
+                      tif->tif_dir.td_nstrips,
+                      isTiled(tif) ? "tiles" : "strips");
+        goto bad;
+    }
     tif->tif_dir.td_stripsperimage = tif->tif_dir.td_nstrips;
     if (tif->tif_dir.td_planarconfig == PLANARCONFIG_SEPARATE)
         tif->tif_dir.td_stripsperimage /= tif->tif_dir.td_samplesperpixel;
