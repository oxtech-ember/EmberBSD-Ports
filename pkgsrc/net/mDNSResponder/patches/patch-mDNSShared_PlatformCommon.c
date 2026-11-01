$NetBSD$

Preserve NetBSD TEST-NET-2 route probing from commit fb006abf2d4: use UDP
echo port 7 in network byte order and log the expected EADDRNOTAVAIL failure at
info level. Retain the pkgsrc fcntl.h portability include.

--- mDNSShared/PlatformCommon.c
+++ mDNSShared/PlatformCommon.c
@@ -33,6 +33,7 @@
 #include <sys/time.h>           // Needed for #include <sys/time.h>().
 #include <assert.h>
 #include <limits.h>
+#include <fcntl.h>
 
 
 #include "mDNSEmbeddedAPI.h"    // Defines the interface provided to the client layer above
@@ -180,7 +181,7 @@
         addr.a4.sin_len         = (unsigned char)inner_len;
         #endif
         addr.a4.sin_family      = AF_INET;
-        addr.a4.sin_port        = 1;    // Not important, any port will do
+        addr.a4.sin_port        = htons(7);    // Not important, any port will do
         addr.a4.sin_addr.s_addr = dst->ip.v4.NotAnInteger;
     }
     else if (dst->type == mDNSAddrType_IPv6)
@@ -191,14 +192,22 @@
         #endif
         addr.a6.sin6_family   = AF_INET6;
         addr.a6.sin6_flowinfo = 0;
-        addr.a6.sin6_port     = 1;  // Not important, any port will do
+        addr.a6.sin6_port     = htons(7);  // Not important, any port will do
         addr.a6.sin6_addr     = *(const struct in6_addr*)&dst->ip.v6;
         addr.a6.sin6_scope_id = 0;
     }
     else return;
 
     if ((connect(sock, &addr.s, inner_len)) < 0)
-    { LogMsg("mDNSPlatformSourceAddrForDest: connect %#a failed errno %d (%s)", dst, errno, strerror(errno)); goto exit; }
+    {
+        static const mDNSv4Addr dummy = { .b = { 198, 51, 100, 42 } };
+        if (dst->type == mDNSAddrType_IPv4 &&
+            dst->ip.v4.NotAnInteger == dummy.NotAnInteger && errno == EADDRNOTAVAIL)
+            LogInfo("mDNSPlatformSourceAddrForDest: connect %#a failed errno %d (%s)", dst, errno, strerror(errno));
+        else
+            LogMsg("mDNSPlatformSourceAddrForDest: connect %#a failed errno %d (%s)", dst, errno, strerror(errno));
+        goto exit;
+    }
 
     if ((getsockname(sock, &addr.s, &len)) < 0)
     { LogMsg("mDNSPlatformSourceAddrForDest: getsockname failed errno %d (%s)", errno, strerror(errno)); goto exit; }
