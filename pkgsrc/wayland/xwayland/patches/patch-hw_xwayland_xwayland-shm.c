$NetBSD$

Origin: EmberBSD (AI-assisted).
Fall back to ftruncate() when posix_fallocate() cannot preallocate the
anonymous shared-memory file, and always size the file with ftruncate().
On NetBSD and EmberBSD a memfd is not a vnode, so posix_fallocate() returns
EINVAL for it. A file system without fallocate support returns EOPNOTSUPP
(EmberBSD: FFS and tmpfs), and a kernel without the call ENOSYS.
os_create_anonymous_file() treated every non-zero result as a failed
allocation, closed the descriptor and returned -1, so no wl_shm pool existed
and the software (shm) path drew X11 windows without content. These three
results mean "not supported", not "no space". Other errors (ENOSPC, EFBIG,
EIO, ...) are still returned to the caller. The NetBSD posix_fallocate(2)
manual page states that the call does not change the file size and
recommends ftruncate() first, so the file is sized explicitly in every case
(a no-op where the call already extended it). libwayland
(cursor/os-compatibility.c) and Mesa (util/disk_cache_os.c) already fall
back to ftruncate() the same way for EINVAL and EOPNOTSUPP.

--- hw/xwayland/xwayland-shm.c.orig
+++ hw/xwayland/xwayland-shm.c
@@ -179,11 +179,28 @@
     } while (ret == EINTR);
     OsReleaseSignals();
 
-    if (ret != 0) {
+    if (ret != 0 && ret != EINVAL && ret != EOPNOTSUPP && ret != ENOSYS) {
         close(fd);
         errno = ret;
         return -1;
     }
+
+    /*
+     * Preallocation is not supported by this descriptor (EINVAL for a memfd
+     * on NetBSD, EOPNOTSUPP for a file system without fallocate, ENOSYS
+     * without the call), or the system does not extend the file size.
+     * Neither is a failure to allocate: size the file with ftruncate(), as
+     * the code below does when posix_fallocate() is unavailable. Real
+     * failures such as ENOSPC, EFBIG or EIO were returned above.
+     */
+    do {
+        ret = ftruncate(fd, size);
+    } while (ret == -1 && errno == EINTR);
+
+    if (ret < 0) {
+        close(fd);
+        return -1;
+    }
 #else
     do {
         ret = ftruncate(fd, size);
