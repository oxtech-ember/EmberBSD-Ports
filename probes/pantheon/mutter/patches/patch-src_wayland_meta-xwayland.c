$NetBSD$

--- src/wayland/meta-xwayland.c.orig	2026-09-15 17:26:39.000000000 +0300
+++ src/wayland/meta-xwayland.c	2026-10-12 23:45:15.285191351 +0300
@@ -599,17 +599,27 @@
 {
   int abstract_fd, unix_fd;
 
+#ifdef __linux__
   abstract_fd = bind_to_abstract_socket (display_index, error);
   if (abstract_fd < 0)
     return FALSE;
+#endif
 
   unix_fd = bind_to_unix_socket (display_index, error);
   if (unix_fd < 0)
     {
+#ifndef __linux__
       close (abstract_fd);
+#endif
       return FALSE;
     }
 
+#ifndef __linux__
+  /* BSD systems have no abstract sockets; both fds point at the
+   * regular X11 unix socket. */
+  abstract_fd = unix_fd;
+#endif
+
   *abstract_fd_out = abstract_fd;
   *unix_fd_out = unix_fd;
 
