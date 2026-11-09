$NetBSD$

Expose the owned FILE reader from KiCad 10.0.8 thirdparty/dxflib_qcad
(GPL-2.0-or-later). Origin: KiCad contributors; adapted by EmberBSD contributors.

--- src/dl_dxf.h.orig
+++ src/dl_dxf.h
@@ -124,6 +124,8 @@
     DL_Dxf();
     ~DL_Dxf();
 
+    // Takes ownership and closes fp, including on read errors or exceptions.
+    bool in(FILE* fp, DL_CreationInterface* creationInterface);
     bool in(const std::string& file,
             DL_CreationInterface* creationInterface);
     bool readDxfGroups(FILE* fp,
