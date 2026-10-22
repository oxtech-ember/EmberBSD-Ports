$NetBSD$

--- src/core/fr-command-7z.c.orig
+++ src/core/fr-command-7z.c
@@ -208,7 +208,9 @@
 static void
 fr_command_7z_begin_command (FrCommand *comm)
 {
-	if (is_program_in_path ("7z"))
+	if (is_program_in_path ("7zz"))
+		fr_process_begin_command (comm->process, "7zz");
+	else if (is_program_in_path ("7z"))
 		fr_process_begin_command (comm->process, "7z");
 	else if (is_program_in_path ("7za"))
 		fr_process_begin_command (comm->process, "7za");
@@ -608,6 +610,14 @@
 }
 
 
+static gboolean
+fr_command_7z_is_available (gboolean check_command)
+{
+	return is_program_available ("7zz", check_command)
+		|| is_program_available ("7z", check_command);
+}
+
+
 static FrCommandCap
 fr_command_7z_get_capabilities (FrCommand  *comm,
 				const char *mime_type,
@@ -616,20 +626,20 @@
 	FrCommandCap capabilities;
 
 	capabilities = FR_COMMAND_CAN_ARCHIVE_MANY_FILES;
-	if (! is_program_available ("7za", check_command) && ! is_program_available ("7zr", check_command) && ! is_program_available ("7z", check_command))
+	if (! is_program_available ("7za", check_command) && ! is_program_available ("7zr", check_command) && ! fr_command_7z_is_available (check_command))
 		return capabilities;
 
 	if (is_mime_type (mime_type, "application/x-7z-compressed")) {
 		capabilities |= FR_COMMAND_CAN_READ_WRITE | FR_COMMAND_CAN_CREATE_VOLUMES;
-		if (is_program_available ("7z", check_command))
+		if (fr_command_7z_is_available (check_command))
 			capabilities |= FR_COMMAND_CAN_ENCRYPT | FR_COMMAND_CAN_ENCRYPT_HEADER;
 	}
 	else if (is_mime_type (mime_type, "application/x-7z-compressed-tar")) {
 		capabilities |= FR_COMMAND_CAN_READ_WRITE;
-		if (is_program_available ("7z", check_command))
+		if (fr_command_7z_is_available (check_command))
 			capabilities |= FR_COMMAND_CAN_ENCRYPT | FR_COMMAND_CAN_ENCRYPT_HEADER;
 	}
-	else if (is_program_available ("7z", check_command)) {
+	else if (fr_command_7z_is_available (check_command)) {
 		capabilities |= FR_COMMAND_CAN_READ;
 
 		if (is_mime_type (mime_type, "application/x-cbz")
@@ -663,11 +673,11 @@
 			    const char *mime_type)
 {
 	if (is_mime_type (mime_type, "application/vnd.rar"))
-		return PACKAGES ("p7zip,p7zip-rar,7zip");
+		return PACKAGES ("7-zip,p7zip-rar");
 	else if (is_mime_type (mime_type, "application/zip") || is_mime_type (mime_type, "application/vnd.ms-cab-compressed"))
-		return PACKAGES ("p7zip,p7zip-full,7zip");
+		return PACKAGES ("7-zip");
 	else
-		return PACKAGES ("p7zip,7zip");
+		return PACKAGES ("7-zip");
 }
 
 
