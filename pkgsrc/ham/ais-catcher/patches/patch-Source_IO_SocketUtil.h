$NetBSD$

Include the standard IPv4 socket definitions on all POSIX platforms.
Origin: EmberBSD; AI-assisted local patch, not submitted upstream.

--- Source/IO/SocketUtil.h.orig
+++ Source/IO/SocketUtil.h
@@ -32,9 +32,7 @@
 #include <unistd.h>
 #include <cerrno>
 #include <cstring>
-#ifdef __ANDROID__
 #include <netinet/in.h>
-#endif
 
 #define SOCKET int
 #define SOCKADDR struct sockaddr
