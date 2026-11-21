$NetBSD$

Use the POSIX TCP protocol level and include its IPv4 definitions on BSD.
Origin: EmberBSD; AI-assisted local patch, not submitted upstream.

--- Source/IO/SocketUtil.h.orig
+++ Source/IO/SocketUtil.h
@@ -39,9 +39,7 @@
 #include <cstring>
 #include <poll.h>
 #include <netinet/tcp.h>
-#ifdef __ANDROID__
 #include <netinet/in.h>
-#endif
 
 #define SOCKET int
 #define SOCKADDR struct sockaddr
@@ -161,15 +159,10 @@
 #if defined(__APPLE__)
 		if (setsockopt(sock, IPPROTO_TCP, TCP_KEEPALIVE, &idle, sizeof(idle)))
 			return false;
-#elif defined(__ANDROID__)
+#else
 		if (setsockopt(sock, IPPROTO_TCP, TCP_KEEPIDLE, &idle, sizeof(idle)) ||
 			setsockopt(sock, IPPROTO_TCP, TCP_KEEPINTVL, &interval, sizeof(interval)) ||
 			setsockopt(sock, IPPROTO_TCP, TCP_KEEPCNT, &count, sizeof(count)))
-			return false;
-#else
-		if (setsockopt(sock, SOL_TCP, TCP_KEEPIDLE, &idle, sizeof(idle)) ||
-			setsockopt(sock, SOL_TCP, TCP_KEEPINTVL, &interval, sizeof(interval)) ||
-			setsockopt(sock, SOL_TCP, TCP_KEEPCNT, &count, sizeof(count)))
 			return false;
 #endif
 #endif
