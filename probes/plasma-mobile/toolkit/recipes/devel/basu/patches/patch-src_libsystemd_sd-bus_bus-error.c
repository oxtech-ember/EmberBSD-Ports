$NetBSD$

Origin: EmberBSD (AI-assisted).
Handle a failed POSIX strerror_r before reading its returned string.
The wrapper returns NULL for errors such as EINVAL. Keep ERANGE retries.

--- src/libsystemd/sd-bus/bus-error.c.orig	2022-12-16 10:13:02.000000000 +0000
+++ src/libsystemd/sd-bus/bus-error.c
@@ -402,13 +402,13 @@ static void bus_error_strerror(sd_bus_error *e, int error) {
 
                 errno = 0;
                 x = _strerror_r(error, m, k);
-                if (errno == ERANGE || strlen(x) >= k - 1) {
+                if (errno == ERANGE || (x && strlen(x) >= k - 1)) {
                         free(m);
                         k *= 2;
                         continue;
                 }
 
-                if (errno) {
+                if (!x || errno) {
                         free(m);
                         return;
                 }
