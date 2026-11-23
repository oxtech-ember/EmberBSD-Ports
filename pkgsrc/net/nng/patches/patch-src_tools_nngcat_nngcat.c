$NetBSD$

Keep the configured receive timeout when no send interval is selected.
Clamp an expired finite interval to a valid zero-duration receive.

--- src/tools/nngcat/nngcat.c.orig
+++ src/tools/nngcat/nngcat.c
@@ -691,11 +691,16 @@
 		// want to increment the iteration count.
 
 		for (;;) {
-			delta = (nng_duration) (nng_clock() - start);
-
-			nng_duration expire = interval - delta;
-			if ((recvtimeo >= 0) && (expire > recvtimeo)) {
-				expire = recvtimeo;
+			nng_duration expire = recvtimeo;
+
+			if (interval >= 0) {
+				nng_time     elapsed = nng_clock() - start;
+				nng_duration remaining = elapsed >= (nng_time) interval
+				    ? 0
+				    : interval - (nng_duration) elapsed;
+				if (expire < 0 || remaining < expire) {
+					expire = remaining;
+				}
 			}
 			rv =
 			    nng_socket_set_ms(sock, NNG_OPT_RECVTIMEO, expire);
