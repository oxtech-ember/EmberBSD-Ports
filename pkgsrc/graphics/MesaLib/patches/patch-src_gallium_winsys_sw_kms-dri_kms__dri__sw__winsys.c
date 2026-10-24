Origin: EmberBSD; AI-assisted Mesa 26.2.5 imported KMS BO mutex repair.
Status: local; not submitted upstream.

Initialize the imported BO map mutex before publishing the displaytarget.
Check initialization in both import constructors. Destroy an initialized
mutex if size discovery or plane creation fails. Keep original Mesa licenses
and authorship unchanged.

--- src/gallium/winsys/sw/kms-dri/kms_dri_sw_winsys.c.orig
+++ src/gallium/winsys/sw/kms-dri/kms_dri_sw_winsys.c
@@ -284,13 +284,17 @@
 
    kms_sw_dt->format = format;
 
-   mtx_init(&kms_sw_dt->map_lock, mtx_plain);
+   if (mtx_init(&kms_sw_dt->map_lock, mtx_plain) != thrd_success) {
+      FREE(kms_sw_dt);
+      return NULL;
+   }
 
    kms_sw_dt->size = whandle->size;
    kms_sw_dt->handle = kms_handle;
    struct kms_sw_plane *plane = get_plane(kms_sw_dt, format, width, height,
                                           stride, whandle->offset);
    if (!plane) {
+      mtx_destroy(&kms_sw_dt->map_lock);
       FREE(kms_sw_dt);
       return NULL;
    }
@@ -406,9 +410,15 @@
    if (!kms_sw_dt)
       return NULL;
 
+   if (mtx_init(&kms_sw_dt->map_lock, mtx_plain) != thrd_success) {
+      FREE(kms_sw_dt);
+      return NULL;
+   }
+
    list_inithead(&kms_sw_dt->planes);
    off_t lseek_ret = lseek(fd, 0, SEEK_END);
    if (lseek_ret == -1) {
+      mtx_destroy(&kms_sw_dt->map_lock);
       FREE(kms_sw_dt);
       return NULL;
    }
@@ -421,6 +431,7 @@
    lseek(fd, 0, SEEK_SET);
    plane = get_plane(kms_sw_dt, format, width, height, stride, offset);
    if (!plane) {
+      mtx_destroy(&kms_sw_dt->map_lock);
       FREE(kms_sw_dt);
       return NULL;
    }
