$NetBSD$

Use the portable TCP protocol level and guard unsupported timeout variables.
Origin: EmberBSD; AI-assisted local patch, not submitted upstream.

--- Source/IO/Protocol.cpp.orig
+++ Source/IO/Protocol.cpp
@@ -160,14 +160,16 @@
 #else
 			int interval = 5;
 			int count = 2;
-			if (setsockopt(sock, SOL_TCP, TCP_KEEPIDLE, &idle, sizeof(idle)) ||
-				setsockopt(sock, SOL_TCP, TCP_KEEPINTVL, &interval, sizeof(interval)) ||
-				setsockopt(sock, SOL_TCP, TCP_KEEPCNT, &count, sizeof(count)))
+			if (setsockopt(sock, IPPROTO_TCP, TCP_KEEPIDLE, &idle, sizeof(idle)) ||
+				setsockopt(sock, IPPROTO_TCP, TCP_KEEPINTVL, &interval, sizeof(interval)) ||
+				setsockopt(sock, IPPROTO_TCP, TCP_KEEPCNT, &count, sizeof(count)))
 				return fail();
 #endif
 
 			// Error a wedged (half-open / zero-window) socket instead of hanging forever.
+#if defined(TCP_USER_TIMEOUT) || (defined(_WIN32) && defined(TCP_MAXRT))
 			const int user_timeout_ms = (idle + 5 * 2) * 1000;
+#endif
 #if defined(TCP_USER_TIMEOUT)
 			if (setsockopt(sock, IPPROTO_TCP, TCP_USER_TIMEOUT, (const char *)&user_timeout_ms, sizeof(user_timeout_ms)))
 				Debug() << "TCP (" << host << ":" << port << "): TCP_USER_TIMEOUT not applied: " << strerror(errno);
