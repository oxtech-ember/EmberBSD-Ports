$NetBSD$

--- src/core/fr-command-tar.c.orig
+++ src/core/fr-command-tar.c
@@ -1158,7 +1158,7 @@
 			capabilities |= FR_COMMAND_CAN_READ_WRITE;
 	}
 	else if (is_mime_type (mime_type, "application/x-7z-compressed-tar")) {
-		const char *try_command[3] = { "7za", "7zr", "7z" };
+		const char *try_command[4] = { "7zz", "7z", "7za", "7zr" };
 		size_t      i;
 
 		for (i = 0; i < G_N_ELEMENTS (try_command); i++) {
@@ -1182,7 +1182,7 @@
 	FR_COMMAND_CLASS (parent_class)->set_mime_type (comm, mime_type);
 
 	if (is_mime_type (mime_type, "application/x-7z-compressed-tar")) {
-		const char *try_command[3] = { "7za", "7zr", "7z" };
+		const char *try_command[4] = { "7zz", "7z", "7za", "7zr" };
 		size_t      i;
 
 		for (i = 0; i < G_N_ELEMENTS (try_command); i++) {
@@ -1222,7 +1222,7 @@
 	else if (is_mime_type (mime_type, "application/x-lzop-compressed-tar"))
 		return PACKAGES ("tar,lzop");
 	else if (is_mime_type (mime_type, "application/x-7z-compressed-tar"))
-		return PACKAGES ("tar,p7zip");
+		return PACKAGES ("tar,7-zip");
 
 	return NULL;
 }
