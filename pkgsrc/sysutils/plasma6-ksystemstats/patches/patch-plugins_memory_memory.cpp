$NetBSD$

Select the NetBSD memory backend.

--- plugins/memory/memory.cpp.orig
+++ plugins/memory/memory.cpp
@@ -11,6 +11,8 @@
 #include "linuxbackend.h"
 #elif defined Q_OS_FREEBSD
 #include "freebsdbackend.h"
+#elif defined Q_OS_NETBSD
+#include "netbsdbackend.h"
 #endif
 
 #include <systemstats/SensorContainer.h>
@@ -26,6 +28,8 @@
     m_backend = std::make_unique<LinuxMemoryBackend>(container);
 #elif defined Q_OS_FREEBSD
     m_backend = std::make_unique<FreeBsdMemoryBackend>(container);
+#elif defined Q_OS_NETBSD
+    m_backend = std::make_unique<NetBsdMemoryBackend>(container);
 #endif
     m_backend->initSensors();
 }
