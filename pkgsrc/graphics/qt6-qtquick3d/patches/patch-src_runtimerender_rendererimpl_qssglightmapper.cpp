Use common external providers for Qt Quick 3D.

--- src/runtimerender/rendererimpl/qssglightmapper.cpp.orig
+++ src/runtimerender/rendererimpl/qssglightmapper.cpp
@@ -16,7 +16,7 @@
 #include <QtConcurrent/qtconcurrentrun.h>
 #include <QRandomGenerator>
 #include <qsimd.h>
-#include <embree3/rtcore.h>
+#include <embree4/rtcore.h>
 #include <QtQuick3DRuntimeRender/private/qssglightmapio_p.h>
 #include <QDir>
 #include <QBuffer>
@@ -1466,9 +1466,9 @@
 
     bool intersect(RTCScene scene)
     {
-        RTCIntersectContext ctx;
-        rtcInitIntersectContext(&ctx);
-        rtcIntersect1(scene, &ctx, &rayhit);
+        RTCIntersectArguments args;
+        rtcInitIntersectArguments(&args);
+        rtcIntersect1(scene, &rayhit, &args);
         return rayhit.hit.geomID != RTC_INVALID_GEOMETRY_ID;
     }
 };
