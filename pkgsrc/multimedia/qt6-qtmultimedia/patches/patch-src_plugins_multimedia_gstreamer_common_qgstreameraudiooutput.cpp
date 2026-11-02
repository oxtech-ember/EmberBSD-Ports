$NetBSD$

Origin: EmberBSD (AI-assisted). Include the standard mutex header used by the GStreamer audio output.

--- src/plugins/multimedia/gstreamer/common/qgstreameraudiooutput.cpp.orig
+++ src/plugins/multimedia/gstreamer/common/qgstreameraudiooutput.cpp
@@ -8,6 +8,8 @@
 #include <QtMultimedia/qaudiodevice.h>
 #include <QtMultimedia/qaudiooutput.h>
 
+#include <mutex>
+
 #include <common/qgstpipeline_p.h>
 #include <audio/qgstreameraudiodevice_p.h>
 
