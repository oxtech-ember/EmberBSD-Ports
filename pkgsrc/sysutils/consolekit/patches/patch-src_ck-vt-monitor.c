Origin: EmberBSD (AI-assisted), local port; not submitted upstream.

Keep the pkgsrc Solaris build fix. Poll actual NetBSD console state without getty counts.
Do not use pre-completion screen-switch event values as active VT numbers.

--- src/ck-vt-monitor.c.orig
+++ src/ck-vt-monitor.c
@@ -56,6 +56,9 @@
 
         GAsyncQueue     *event_queue;
         guint            process_queue_id;
+#ifdef __NetBSD__
+        guint            native_poll_id;
+#endif
 };
 
 enum {
@@ -76,8 +79,10 @@
 
 G_DEFINE_TYPE (CkVtMonitor, ck_vt_monitor, G_TYPE_OBJECT)
 
+#ifndef __NetBSD__
 G_LOCK_DEFINE_STATIC (hash_lock);
 G_LOCK_DEFINE_STATIC (schedule_lock);
+#endif
 
 static gpointer vt_object = NULL;
 
@@ -99,10 +104,20 @@
 {
         gboolean ret;
         int      res;
+#ifdef __NetBSD__
+        guint    current_num;
+#endif
 
         g_return_val_if_fail (CK_IS_VT_MONITOR (vt_monitor), FALSE);
 
+#ifdef __NetBSD__
+        if (! ck_vt_monitor_get_active (vt_monitor, &current_num, error)) {
+                return FALSE;
+        }
+        if (num == current_num) {
+#else
         if (num == vt_monitor->priv->active_num) {
+#endif
                 g_set_error (error,
                              CK_VT_MONITOR_ERROR,
                              CK_VT_MONITOR_ERROR_ALREADY_ACTIVE,
@@ -137,10 +152,15 @@
                           guint32        *num,
                           GError        **error)
 {
+#ifdef __NetBSD__
+        guint active;
+#else
         if (num != NULL) {
                 *num = 0;
         }
 
+#endif
+
         g_return_val_if_fail (CK_IS_VT_MONITOR (vt_monitor), FALSE);
 
         if (vt_monitor->priv->vfd == ERROR) {
@@ -151,16 +171,27 @@
                 return FALSE;
         }
 
+#ifdef __NetBSD__
+        if (! ck_get_active_console_num (vt_monitor->priv->vfd, &active)) {
+                g_set_error (error, CK_VT_MONITOR_ERROR, CK_VT_MONITOR_ERROR_GENERAL,
+                             _("Unable to query active console: %s"), g_strerror (errno));
+                return FALSE;
+        }
+        if (num != NULL) {
+                *num = active;
+        }
+#else
         if (num != NULL) {
                 *num = vt_monitor->priv->active_num;
         }
+#endif
 
         return TRUE;
 }
 
 #if defined (__sun) && defined (HAVE_SYS_VT_H)
 static void
-handle_vt_active (void)
+handle_vt_active (int)
 {
         struct vt_stat state;
         guint          num;
@@ -215,6 +246,26 @@
         }
 }
 
+#ifdef __NetBSD__
+static gboolean
+native_poll_active (gpointer data)
+{
+        CkVtMonitor *vt_monitor = CK_VT_MONITOR (data);
+        guint num;
+
+        /* A signal consumer can release the last external reference. */
+        g_object_ref (vt_monitor);
+        if (! ck_get_active_console_num (vt_monitor->priv->vfd, &num)) {
+                if (vt_monitor->priv->active_num != 0) {
+                        g_warning ("Unable to query active native console: %s", g_strerror (errno));
+                }
+                num = 0;
+        }
+        change_active_num (vt_monitor, num);
+        g_object_unref (vt_monitor);
+        return G_SOURCE_CONTINUE;
+}
+#else
 typedef struct {
         gint32       num;
         CkVtMonitor *vt_monitor;
@@ -402,10 +453,17 @@
         }
 }
 
+#endif /* !__NetBSD__ */
+
 static void
 vt_add_watches (CkVtMonitor *vt_monitor)
 {
-#if defined (__sun) && !defined (HAVE_SYS_VT_H) || (defined(__OpenBSD__) && (!defined(__i386__) && !defined(__amd64__) && !defined(__powerpc__) && !defined(__aarch64__)))
+#ifdef __NetBSD__
+        /* Query committed kernel state. Screen-switch events precede completion. */
+        if (vt_monitor->priv->native_poll_id == 0) {
+                vt_monitor->priv->native_poll_id = g_timeout_add (100, native_poll_active, vt_monitor);
+        }
+#elif defined (__sun) && !defined (HAVE_SYS_VT_H) || (defined(__OpenBSD__) && (!defined(__i386__) && !defined(__amd64__) && !defined(__powerpc__) && !defined(__aarch64__)))
         /* Best to do nothing if VT is not supported */
 #elif defined (__sun) && defined (HAVE_SYS_VT_H)
         /*
@@ -512,8 +570,10 @@
                 }
 
                 vt_monitor->priv->active_num = active;
+#ifndef __NetBSD__
                 vt_monitor->priv->event_queue = g_async_queue_new ();
                 vt_monitor->priv->vt_thread_hash = g_hash_table_new (g_direct_hash, g_direct_equal);
+#endif
 
                 vt_add_watches (vt_monitor);
         }
@@ -533,6 +593,13 @@
 
         g_return_if_fail (vt_monitor->priv != NULL);
 
+#ifdef __NetBSD__
+        if (vt_monitor->priv->native_poll_id > 0) {
+                g_source_remove (vt_monitor->priv->native_poll_id);
+                vt_monitor->priv->native_poll_id = 0;
+        }
+#endif
+
         if (vt_monitor->priv->process_queue_id > 0) {
                 g_source_remove (vt_monitor->priv->process_queue_id);
                 vt_monitor->priv->process_queue_id = 0;
