$NetBSD$

Origin: EmberBSD (AI-assisted). Add the standard mutex declaration used by the GStreamer pad helper.

--- src/plugins/multimedia/gstreamer/common/qgst_p.h.orig
+++ src/plugins/multimedia/gstreamer/common/qgst_p.h
@@ -40,6 +40,7 @@
 
 #include "qgst_handle_types_p.h"
 
+#include <mutex>
 #include <type_traits>
 #ifdef __cpp_lib_three_way_comparison
 #  include <compare>
