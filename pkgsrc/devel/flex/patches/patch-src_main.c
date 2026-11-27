$NetBSD$

Resolve Darwin tools from the installed prefix. Select base m4 for the NetBSD target.
Origin: EmberBSD contributors (AI-assisted).

--- src/main.c.orig
+++ src/main.c
@@ -40,6 +40,32 @@
 #include "options.h"
 #include "tables.h"
 #include "parse.h"
+#ifdef FLEX_DARWIN_M4
+#include <limits.h>
+#include <mach-o/dyld.h>
+
+/* Use the installed executable also when the caller uses a symlink. */
+static void
+darwin_prefix_path (char path[PATH_MAX], const char *relative)
+{
+	char executable[PATH_MAX], resolved[PATH_MAX], *slash;
+	uint32_t length = sizeof (executable);
+
+	if (_NSGetExecutablePath (executable, &length) != 0 ||
+	    realpath (executable, resolved) == NULL)
+		lerr_fatal (_("cannot resolve the flex executable"));
+	slash = strrchr (resolved, '/');
+	if (slash != NULL) {
+		*slash = '\0';
+		slash = strrchr (resolved, '/');
+	}
+	if (slash == NULL)
+		lerr_fatal (_("cannot resolve the flex installation prefix"));
+	*slash = '\0';
+	if (snprintf (path, PATH_MAX, "%s/%s", resolved, relative) >= PATH_MAX)
+		lerr_fatal (_("flex installation path is too long"));
+}
+#endif
 
 static char flex_version[] = FLEX_VERSION;
 
@@ -293,7 +319,14 @@
 	setlocale (LC_MESSAGES, "");
         setlocale (LC_CTYPE, "");
 	textdomain (PACKAGE);
+#ifdef FLEX_DARWIN_M4
+	char localedir[PATH_MAX];
+
+	darwin_prefix_path (localedir, FLEX_DARWIN_LOCALEDIR);
+	bindtextdomain (PACKAGE, localedir);
+#else
 	bindtextdomain (PACKAGE, LOCALEDIR);
+#endif
 #endif
 #endif
 
@@ -320,7 +353,16 @@
 
 	output_chain = filter_create_int(NULL, filter_tee_header, env.headerfilename);
 	if ( !(m4 = getenv("M4"))) {
+#ifdef FLEX_DARWIN_M4
+		static char installed_m4[PATH_MAX];
+
+		darwin_prefix_path (installed_m4, "bin/" FLEX_DARWIN_M4);
+		m4 = installed_m4;
+#elif defined(FLEX_TARGET_M4) && !defined(USE_CONFIG_FOR_BUILD)
+		m4 = FLEX_TARGET_M4;
+#else
 		m4 = M4;
+#endif
 	}
 	filter_create_ext(output_chain, m4, "-P", (char *) 0);
 	filter_create_int(output_chain, filter_fix_linedirs, NULL);
