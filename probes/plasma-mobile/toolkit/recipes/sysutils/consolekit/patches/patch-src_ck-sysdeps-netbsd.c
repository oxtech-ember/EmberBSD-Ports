Origin: EmberBSD (AI-assisted), local port; not submitted upstream.

Use absolute NetBSD TTY paths and parse canonical console numbers without overflow.
Reject unknown active consoles and preserve caller output on failed kernel queries.
Validate complete live process snapshots before UID, stat, or environment queries.
Keep invalid outputs initialized and release failed process-stat allocations.
This metadata check does not establish session or cookie authority.

--- src/ck-sysdeps-netbsd.c.orig
+++ src/ck-sysdeps-netbsd.c
@@ -36,6 +36,7 @@
 #include <sys/types.h>
 #include <sys/stat.h>
 #include <sys/sysctl.h>
+#include <sys/proc.h>
 #include <sys/ioctl.h>
 
 #ifdef HAVE_SYS_MOUNT_H
@@ -70,6 +71,7 @@
         unsigned long long cutime;      /* stat            cumulative utime of process and reaped children */
         unsigned long long cstime;      /* stat            cumulative stime of process and reaped children */
         unsigned long long start_time;  /* stat            start time of process -- seconds since 1-1-70 */
+        unsigned int start_time_usec;   /* NetBSD process start microseconds */
         unsigned long start_code;       /* stat            address of beginning of code segment */
         unsigned long end_code;         /* stat            address of end of code segment */
         unsigned long start_stack;      /* stat            address of the bottom of stack for the process */
@@ -124,17 +126,48 @@
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
 get_kinfo_proc2 (pid_t pid,
                 struct kinfo_proc2 *p)
 {
+        struct kinfo_proc2 snapshot;
         int    mib[6];
         size_t len;
 
-        len = sizeof(struct kinfo_proc2);
+        if (p == NULL) {
+                errno = EINVAL;
+                return FALSE;
+        }
+        memset (p, 0, sizeof *p);
+        if (pid <= 1) {
+                errno = EINVAL;
+                return FALSE;
+        }
+
+        memset (&snapshot, 0, sizeof snapshot);
+        len = sizeof snapshot;
         mib[0] = CTL_KERN;
         mib[1] = KERN_PROC2;
         mib[2] = KERN_PROC_PID;
@@ -142,11 +175,27 @@
         mib[4] = len;
         mib[5] = 1;
 
-        if (sysctl (mib, 6, p, &len, NULL, 0) == -1) {
-                g_warning ("sysctl kern.proc2.pid failed: %s", g_strerror (errno));
+        if (sysctl (mib, 6, &snapshot, &len, NULL, 0) == -1) {
+                int saved_errno = errno;
+                g_warning ("sysctl kern.proc2.pid failed: %s", g_strerror (saved_errno));
+                errno = saved_errno;
                 return FALSE;
         }
 
+        /* A missing PID can return success with no record. */
+        if (len != sizeof snapshot) {
+                errno = len == 0 ? ESRCH : EIO;
+                return FALSE;
+        }
+        /* p_stat describes an LWP; p_realstat describes the process. */
+        if (snapshot.p_pid != pid || snapshot.p_uvalid == 0 ||
+            (snapshot.p_realstat != SACTIVE && snapshot.p_realstat != SSTOP) ||
+            snapshot.p_ustart_sec == 0 || snapshot.p_ustart_usec >= 1000000) {
+                errno = ESRCH;
+                return FALSE;
+        }
+
+        *p = snapshot;
         return TRUE;
 }
 
@@ -177,6 +226,7 @@
         P->rss        = p.p_vm_rssize;
         P->vsize      = (unsigned long) p.p_vm_vsize;
         P->start_time = p.p_ustart_sec;
+        P->start_time_usec = p.p_ustart_usec;
         P->wchan      = (unsigned long) p.p_wchan;
         P->state      = p.p_stat;
         P->nice       = p.p_nice;
@@ -201,11 +251,14 @@
         gboolean       res;
         CkProcessStat *proc;
 
-        g_return_val_if_fail (pid > 1, FALSE);
-
         if (stat == NULL) {
                 return FALSE;
         }
+        *stat = NULL;
+        if (pid <= 1) {
+                errno = EINVAL;
+                return FALSE;
+        }
 
         proc = g_new0 (CkProcessStat, 1);
         proc->pid = pid;
@@ -213,7 +266,7 @@
         if (res) {
                 *stat = proc;
         } else {
-                *stat = NULL;
+                g_free (proc);
         }
 
         return res;
@@ -235,6 +288,11 @@
         struct kinfo_proc2 p;
         int               i;
 
+        if (pid <= 1) {
+                errno = EINVAL;
+                return NULL;
+        }
+
         kd = kvm_openfiles (NULL, NULL, NULL, KVM_NO_FILES, errbuf);
         if (kd == NULL) {
                 g_warning ("kvm_openfiles failed: %s", errbuf);
@@ -305,7 +363,10 @@
         gboolean          res;
         struct kinfo_proc2 p;
 
-        g_return_val_if_fail (pid > 1, 0);
+        if (pid <= 1) {
+                errno = EINVAL;
+                return (uid_t) -1;
+        }
 
         uid = -1;
 
@@ -371,6 +432,10 @@
 {
         char *device;
 
+        if (num == 0) {
+                return NULL;
+        }
+
         /* The device number is always one less than the VT number. */
         num--;
 
@@ -383,57 +448,59 @@
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
