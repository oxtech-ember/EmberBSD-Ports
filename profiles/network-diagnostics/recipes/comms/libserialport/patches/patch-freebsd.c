$NetBSD$

NetBSD support by EmberBSD: keep the termios /dev enumeration for
NetBSD — dial-out (dty) device names, because dial-in twins open
with ENXIO without carrier; DT_UNKNOWN dirents fall back to stat;
initialize the return code before the scan; provide an O_TTY_INIT
fallback — and compile the FreeBSD libusb20 metadata path only when
port metadata is built at all; it is not on NetBSD, where
NO_PORT_METADATA is set by the configure patch.

--- freebsd.c.orig	2020-01-26 13:24:07.000000000 +0000
+++ freebsd.c
@@ -86,8 +86,21 @@
 #include <sys/types.h>
 #include <sys/sysctl.h>
 #include <dirent.h>
+#ifdef __NetBSD__
+/*
+ * NetBSD port by EmberBSD: libusb20 is FreeBSD-only, so port metadata
+ * stays unavailable (NO_PORT_METADATA) while the termios-based /dev
+ * enumeration below lists NetBSD dial-out (dty) devices and copes with
+ * the DT_UNKNOWN dirent type of the static /dev directory.
+ */
+#include <sys/stat.h>
+#ifndef O_TTY_INIT
+#define O_TTY_INIT 0
+#endif
+#else
 #include <libusb20.h>
 #include <libusb20_desc.h>
+#endif
 #include "libserialport.h"
 #include "libserialport_internal.h"
 
@@ -114,6 +127,7 @@
 	return 0;
 }
 
+#ifndef NO_PORT_METADATA
 static int libusb_query_port(struct libusb20_device *dev, int idx,
 			     char **drv_name_str, char **drv_inst_str)
 {
@@ -321,6 +335,7 @@
 
 	RETURN_OK();
 }
+#endif /* !NO_PORT_METADATA */
 
 SP_PRIV enum sp_return list_ports(struct sp_port ***list)
 {
@@ -334,21 +349,35 @@
 	if (!(dir = opendir("/dev")))
 		RETURN_FAIL("Could not open dir /dev");
 
+	ret = SP_OK;
+
 	DEBUG("Iterating over results");
 	while ((entry = readdir(dir))) {
 		ret = SP_OK;
-		if (entry->d_type != DT_CHR)
+		if (entry->d_type != DT_CHR && entry->d_type != DT_UNKNOWN)
 			continue;
 		if (strncmp(entry->d_name, "cuaU", 4) != 0)
 			if (strncmp(entry->d_name, "cuau", 4) != 0)
 				if (strncmp(entry->d_name, "cuad", 4) != 0)
-					continue;
+					/*
+					 * NetBSD: list the dial-out
+					 * devices; the dial-in twins
+					 * open with ENXIO when no
+					 * carrier is present.
+					 */
+					if (strncmp(entry->d_name, "dty", 3) != 0)
+						continue;
 		if (strend(entry->d_name, ".init"))
 			continue;
 		if (strend(entry->d_name, ".lock"))
 			continue;
 
 		snprintf(name, sizeof(name), "/dev/%s", entry->d_name);
+		if (entry->d_type == DT_UNKNOWN) {
+			struct stat st;
+			if (stat(name, &st) != 0 || !S_ISCHR(st.st_mode))
+				continue;
+		}
 		DEBUG_FMT("Found device %s", name);
 
 		/* Check that we can open tty/cua device in rw mode - we need that. */
