Origin: EmberBSD; AI-assisted V3D mutex lifecycle repair, not submitted upstream.

Mesa 26.3 initializes the BO cache mutex before the screen is published.
Check both mutex initializations. Unwind only acquired resources on creation errors.
Drain the BO cache before destroying its mutex on normal screen teardown.

--- src/gallium/drivers/v3d/v3d_screen.c.orig
+++ src/gallium/drivers/v3d/v3d_screen.c
@@ -79,6 +79,8 @@ v3d_screen_destroy(struct pipe_screen *pscreen)
 
         _mesa_hash_table_destroy(screen->bo_handles, NULL);
         v3d_bufmgr_destroy(pscreen);
+        mtx_destroy(&screen->bo_handles_mutex);
+        mtx_destroy(&screen->bo_cache.lock);
         slab_destroy_parent(&screen->transfer_pool);
         if (screen->ro)
                 screen->ro->destroy(screen->ro);
@@ -782,6 +784,9 @@ v3d_screen_create(int fd, const struct pipe_screen_config *config,
         struct v3d_screen *screen = rzalloc(NULL, struct v3d_screen);
         struct pipe_screen *pscreen;
 
+        if (!screen)
+                goto fail_fd;
+
         pscreen = &screen->base;
 
         pscreen->destroy = v3d_screen_destroy;
@@ -794,9 +799,13 @@ v3d_screen_create(int fd, const struct pipe_screen_config *config,
         screen->ro = ro;
 
         list_inithead(&screen->bo_cache.time_list);
-        (void)mtx_init(&screen->bo_cache.lock, mtx_plain);
-        (void)mtx_init(&screen->bo_handles_mutex, mtx_plain);
+        if (mtx_init(&screen->bo_cache.lock, mtx_plain) != thrd_success)
+                goto fail_screen;
+        if (mtx_init(&screen->bo_handles_mutex, mtx_plain) != thrd_success)
+                goto fail_cache_mutex;
         screen->bo_handles = util_hash_table_create_ptr_keys();
+        if (!screen->bo_handles)
+                goto fail_handles_mutex;
 
 #if USE_V3D_SIMULATOR
         screen->sim_file = v3d_simulator_init(screen->fd);
@@ -884,7 +893,17 @@ v3d_screen_create(int fd, const struct pipe_screen_config *config,
         return pscreen;
 
 fail:
+#if USE_V3D_SIMULATOR
+        v3d_simulator_destroy(screen->sim_file);
+#endif
+        _mesa_hash_table_destroy(screen->bo_handles, NULL);
+fail_handles_mutex:
+        mtx_destroy(&screen->bo_handles_mutex);
+fail_cache_mutex:
+        mtx_destroy(&screen->bo_cache.lock);
+fail_screen:
+        ralloc_free(screen);
+fail_fd:
         close(fd);
-        ralloc_free(pscreen);
         return NULL;
 }
