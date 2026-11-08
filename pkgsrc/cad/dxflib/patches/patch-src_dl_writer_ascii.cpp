$NetBSD$

Use bounded formatting and return safely for null string input.
--- src/dl_writer_ascii.cpp.orig
+++ src/dl_writer_ascii.cpp
@@ -61,10 +61,10 @@
 void DL_WriterA::dxfReal(int gc, double value) const {
     char str[256];
     if (version==DL_Codes::AC1009_MIN) {
-        sprintf(str, "%.6lf", value);
+        snprintf(str, sizeof(str), "%.6lf", value);
     }
     else {
-        sprintf(str, "%.16lf", value);
+        snprintf(str, sizeof(str), "%.16lf", value);
     }
     
     // fix for german locale:
@@ -112,7 +112,7 @@
  */
 void DL_WriterA::dxfHex(int gc, int value) const {
     char str[12];
-    sprintf(str, "%0X", value);
+    snprintf(str, sizeof(str), "%0X", value);
     dxfString(gc, str);
 }
 
@@ -126,9 +126,8 @@
  */
 void DL_WriterA::dxfString(int gc, const char* value) const {
     if (value==NULL) {
-#ifndef __GCC2x__
-        //throw DL_NullStrExc();
-#endif
+        // The exception is disabled for GCC compatibility; avoid dereferencing NULL.
+        return;
     }
     m_ofile << (gc<10 ? "  " : (gc<100 ? " " : "")) << gc << "\n"
     << value << "\n";
