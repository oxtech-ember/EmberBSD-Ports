$NetBSD$

NetBSD has no O_PATH; open the state directory read-only instead.
Handle the snprintf truncation GCC 16 reports in the override scan.

--- src/pipewire/conf.c.orig	2026-10-13
+++ src/pipewire/conf.c
@@ -339,7 +339,12 @@
 	}
 	return -ENOENT;
 found:
-	if ((res = open(path, O_CLOEXEC | O_DIRECTORY | O_PATH)) < 0) {
+	#ifdef O_PATH
+	int open_flags = O_CLOEXEC | O_DIRECTORY | O_PATH;
+#else
+	int open_flags = O_CLOEXEC | O_DIRECTORY | O_RDONLY;
+#endif
+	if ((res = open(path, open_flags)) < 0) {
 		pw_log_error("Can't open state directory %s: %m", path);
 		return -errno;
 	}
@@ -522,7 +527,9 @@
 		for (i = 0; i < n; i++) {
 			const char *name = entries[i]->d_name;
 
-			snprintf(fname, sizeof(fname), "%s/%s", path, name);
+			if (snprintf(fname, sizeof(fname), "%s/%s", path, name)
+					>= (int)sizeof(fname))
+				continue;
 			if (check_override(conf, name, level)) {
 				if (conf_load(fname, override) >= 0)
 					add_override(conf, override, fname, name, level, i);
