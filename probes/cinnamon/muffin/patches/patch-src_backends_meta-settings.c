diff --git a/src/backends/meta-settings.c b/src/backends/meta-settings.c
index 7bf3ffd..ff034ca 100644
--- src/backends/meta-settings.c.orig
+++ src/backends/meta-settings.c
@@ -28,7 +28,6 @@
 #include "backends/meta-backend-private.h"
 #include "backends/meta-logical-monitor.h"
 #include "backends/meta-monitor-manager-private.h"
-#include "ui/theme-private.h"
 
 #ifndef XWAYLAND_GRAB_DEFAULT_ACCESS_RULES
 # warning "XWAYLAND_GRAB_DEFAULT_ACCESS_RULES is not set"
