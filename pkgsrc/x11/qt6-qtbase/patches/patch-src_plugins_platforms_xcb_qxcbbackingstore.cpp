$NetBSD$

Keep System V shared memory attachable until the X server has attached.

--- src/plugins/platforms/xcb/qxcbbackingstore.cpp.orig
+++ src/plugins/platforms/xcb/qxcbbackingstore.cpp
@@ -379,16 +379,19 @@
 
     void *addr = shmat(id, nullptr, 0);
     if (addr == (void *)-1) {
-        qCWarning(lcQpaXcb, "shmat() failed (%d: %s) for id %d", errno, strerror(errno), id);
+        const int shmatError = errno;
+        qCWarning(lcQpaXcb, "shmat() failed (%d: %s) for id %d",
+                  shmatError, strerror(shmatError), id);
+        if (shmctl(id, IPC_RMID, nullptr) == -1)
+            qCWarning(lcQpaXcb, "Error while marking the shared memory segment to be destroyed");
         return false;
     }
 
-    if (shmctl(id, IPC_RMID, nullptr) == -1)
-        qCWarning(lcQpaXcb, "Error while marking the shared memory segment to be destroyed");
-
     const auto seg = xcb_generate_id(c);
     auto cookie = xcb_shm_attach_checked(c, seg, id, false);
     auto *error = xcb_request_check(c, cookie);
+    if (shmctl(id, IPC_RMID, nullptr) == -1)
+        qCWarning(lcQpaXcb, "Error while marking the shared memory segment to be destroyed");
     if (error) {
         qCWarning(lcQpaXcb(), "xcb_shm_attach() failed");
         free(error);
