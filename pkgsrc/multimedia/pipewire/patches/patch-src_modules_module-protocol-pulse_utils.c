$NetBSD$

NetBSD: statvfs() and the puffs type name instead of statfs() and FUSE_SUPER_MAGIC.

--- src/modules/module-protocol-pulse/utils.c.orig
+++ src/modules/module-protocol-pulse/utils.c
@@ -18,6 +18,9 @@
 #ifdef HAVE_SYS_VFS_H
 #include <sys/vfs.h>
 #endif
+#ifdef __NetBSD__
+#include <sys/statvfs.h>
+#endif
 #ifdef HAVE_PWD_H
 #include <pwd.h>
 #endif
@@ -87,14 +90,22 @@
 	if (root_fd == -1) {
 		res = -errno;
 		if (res == -EACCES) {
-			struct statfs buf;
 			/* Access to the root dir isn't allowed. This can happen if the root is on a fuse
 			 * filesystem, such as in a toolbox container. We will never have a fuse rootfs
 			 * in the flatpak case, so in that case its safe to ignore this and
 			 * continue to detect other types of apps. */
+#ifdef __NetBSD__
+			/* NetBSD runs FUSE file systems on puffs ("puffs|..."). */
+			struct statvfs buf;
+			if (statvfs(root_path, &buf) == 0 &&
+			    strncmp(buf.f_fstypename, "puffs", 5) == 0)
+				return 0;
+#else
+			struct statfs buf;
 			if (statfs(root_path, &buf) == 0 &&
 			    buf.f_type == 0x65735546) /* FUSE_SUPER_MAGIC */
 				return 0;
+#endif
 		}
 		/* Not able to open the root dir shouldn't happen. Probably the app died and
 		 * we're failing due to /proc/$pid not existing. In that case fail instead
