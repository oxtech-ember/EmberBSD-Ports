$NetBSD: patch-src_update-mime-database.cpp,v 1.1 2023/12/05 20:15:23 markd Exp $

Include the pkgsrc data directory in the default search path. Native Darwin
packages take it from the installed executable so the SDK can be moved.

--- src/update-mime-database.cpp.orig
+++ src/update-mime-database.cpp
@@ -23,6 +23,10 @@
 
 #include <algorithm>
 #include <filesystem>
+#ifdef PKGSRC_RELOCATABLE_MIME
+#include <dlfcn.h>
+#include <string>
+#endif
 #include <vector>
 #include <optional>
 
@@ -2156,9 +2160,23 @@
 	}
 
 	env = getenv("XDG_DATA_DIRS");
-	if (!env)
-		env = "/usr/local/share/" PATH_SEPARATOR "/usr/share/";
-	dirs = g_strsplit(env, PATH_SEPARATOR, 0);
+	if (env)
+		dirs = g_strsplit(env, PATH_SEPARATOR, 0);
+	else {
+#ifdef PKGSRC_RELOCATABLE_MIME
+		std::string defaults = "/usr/local/share/" PATH_SEPARATOR "/usr/share/";
+		Dl_info info;
+		if (dladdr(reinterpret_cast<const void *>(&check_in_path_xdg_data), &info) && info.dli_fname) {
+			std::error_code error;
+			auto executable = fs::canonical(info.dli_fname, error);
+			if (!error)
+				defaults.insert(0, (executable.parent_path().parent_path() / "share").string() + PATH_SEPARATOR);
+		}
+		dirs = g_strsplit(defaults.c_str(), PATH_SEPARATOR, 0);
+#else
+		dirs = g_strsplit(PREFIX "/share/" PATH_SEPARATOR "/usr/local/share/" PATH_SEPARATOR "/usr/share/", PATH_SEPARATOR, 0);
+#endif
+	}
 	g_return_if_fail(dirs != NULL);
 	for (n = 0; dirs[n]; n++)
 		;
