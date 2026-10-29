Preserve native NetBSD build compatibility.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- pcap-usb-linux.c.orig
+++ pcap-usb-linux.c
@@ -49,7 +49,9 @@
 #include <limits.h>
 #include <string.h>
 #include <dirent.h>
+#ifdef __linux__
 #include <byteswap.h>
+#endif
 #include <netinet/in.h>
 #include <sys/ioctl.h>
 #include <sys/mman.h>
