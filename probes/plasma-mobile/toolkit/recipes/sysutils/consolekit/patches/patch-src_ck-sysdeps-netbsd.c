Origin: EmberBSD (AI-assisted), local port; not submitted upstream.

Use absolute NetBSD TTY paths and parse canonical console numbers without overflow.
Reject unknown active consoles and preserve caller output on failed kernel queries.

--- src/ck-sysdeps-netbsd.c.orig
+++ src/ck-sysdeps-netbsd.c
@@ -124,7 +124,26 @@
                 return NULL;
         }
 
-        return g_strdup(devname (stat->tty, S_IFCHR));
+        const char *name = devname (stat->tty, S_IFCHR);
+        char **parts;
+        char **part;
+        char *device;
+
+        if (name == NULL || name[0] == '\0' || name[0] == '/') {
+                return NULL;
+        }
+
+        parts = g_strsplit (name, "/", -1);
+        for (part = parts; *part != NULL; part++) {
+                if ((*part)[0] == '\0' || g_str_equal (*part, ".") || g_str_equal (*part, "..")) {
+                        g_strfreev (parts);
+                        return NULL;
+                }
+        }
+        g_strfreev (parts);
+
+        device = g_strconcat ("/dev/", name, NULL);
+        return device;
 }
 
 static gboolean
@@ -371,6 +390,10 @@
 {
         char *device;
 
+        if (num == 0) {
+                return NULL;
+        }
+
         /* The device number is always one less than the VT number. */
         num--;
 
@@ -383,57 +406,59 @@
 ck_get_console_num_from_device (const char *device,
                                 guint      *num)
 {
-        guint    n;
-        gboolean ret;
+        const char *p;
+        guint n = 0;
 
-        n = 0;
-        ret = FALSE;
+        if (device == NULL || !g_str_has_prefix (device, "/dev/ttyE")) {
+                return FALSE;
+        }
 
-        if (device == NULL) {
+        p = device + strlen ("/dev/ttyE");
+        if (p[0] < '0' || p[0] > '9' || (p[0] == '0' && p[1] != '\0')) {
                 return FALSE;
         }
 
-        if (sscanf (device, "/dev/ttyE%u", &n) == 1) {
-                /* The VT number is always one more than the device number. */
-                n++;
-                ret = TRUE;
+        while (*p >= '0' && *p <= '9') {
+                guint digit = *p - '0';
+                /* Reserve one for the one-based VT number. */
+                if (n > (G_MAXUINT - 1 - digit) / 10) {
+                        return FALSE;
+                }
+                n = n * 10 + digit;
+                p++;
+        }
+        if (*p != '\0') {
+                return FALSE;
         }
 
         if (num != NULL) {
-                *num = n;
+                *num = n + 1;
         }
 
-        return ret;
+        return TRUE;
 }
 
 gboolean
 ck_get_active_console_num (int    console_fd,
                            guint *num)
 {
-        gboolean ret;
-        int      res;
-        int      active;
+        int active;
 
         g_assert (console_fd != -1);
 
-        active = 0;
-        ret = FALSE;
-
-        res = ioctl (console_fd, VT_GETACTIVE, &active);
-        if (res == ERROR) {
-                perror ("ioctl VT_GETACTIVE");
-                goto out;
+        if (ioctl (console_fd, VT_GETACTIVE, &active) == -1) {
+                return FALSE;
+        }
+        if (active <= 0) {
+                errno = ENXIO;
+                return FALSE;
         }
 
         g_debug ("Active VT is: %d (ttyE%d)", active, active - 1);
-        ret = TRUE;
-
- out:
         if (num != NULL) {
                 *num = active;
         }
-
-        return ret;
+        return TRUE;
 }
 
 gboolean
