$NetBSD$

Preserve POINT thickness and POLYLINE vertex widths from KiCad 10.0.8
thirdparty/dxflib_qcad (GPL-2.0-or-later). Origin: KiCad contributors;
adapted by EmberBSD contributors. Source license notices remain unchanged.

--- src/dl_entities.h.orig
+++ src/dl_entities.h
@@ -199,10 +199,11 @@
      * Constructor.
      * Parameters: see member variables.
      */
-    DL_PointData(double px=0.0, double py=0.0, double pz=0.0) {
+    DL_PointData(double px=0.0, double py=0.0, double pz=0.0, double pThickness=0.0) {
         x = px;
         y = py;
         z = pz;
+        thickness = pThickness;
     }
 
     /*! X Coordinate of the point. */
@@ -211,6 +212,8 @@
     double y;
     /*! Z Coordinate of the point. */
     double z;
+    /*! DXF group 39: point thickness. */
+    double thickness;
 };
 
 
@@ -419,11 +422,13 @@
      * Parameters: see member variables.
      */
     DL_VertexData(double px=0.0, double py=0.0, double pz=0.0,
-                  double pBulge=0.0) {
+                  double pBulge=0.0, double pStartWidth=0.0, double pEndWidth=0.0) {
         x = px;
         y = py;
         z = pz;
         bulge = pBulge;
+        startWidth = pStartWidth;
+        endWidth = pEndWidth;
     }
 
     /*! X Coordinate of the vertex. */
@@ -435,6 +440,9 @@
     /*! Bulge of vertex.
      * (The tangent of 1/4 of the arc angle or 0 for lines) */
     double bulge;
+    /*! DXF groups 40/41: widths of a POLYLINE vertex. */
+    double startWidth;
+    double endWidth;
 };
 
 
