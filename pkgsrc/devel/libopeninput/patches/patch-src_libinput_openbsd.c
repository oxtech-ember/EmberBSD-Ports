$NetBSD$

KWin uses libinput_device_get_sysname() as part of a D-Bus object path.
Return the wscons sysname, not its /dev node path, matching Linux semantics.

--- src/libinput_openbsd.c.orig
+++ src/libinput_openbsd.c
@@ -3268,7 +3268,10 @@ libinput_device_get_device_group(struct libinput_device *device)
 LIBINPUT_EXPORT const char *
 libinput_device_get_sysname(struct libinput_device *device)
 {
-	return device->devname;
+	if (strncmp(device->devname, "/dev/", 5) == 0)
+		return device->devname + 5; /* skip /dev/ */
+	else
+		return device->devname;
 }
 
 LIBINPUT_EXPORT const char *
