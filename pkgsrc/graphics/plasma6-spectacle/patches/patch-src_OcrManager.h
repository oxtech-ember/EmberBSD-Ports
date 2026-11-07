$NetBSD$

Use the local compatibility header so the screenshot build compiles
without a Tesseract installation.

--- src/OcrManager.h.orig
+++ src/OcrManager.h
@@ -18,7 +18,7 @@
 
 #include <memory>
 
-#include <tesseract/capi.h>
+#include "TesseractCompatibility.h"
 
 /**
  * @brief Worker class for OCR processing in background thread
