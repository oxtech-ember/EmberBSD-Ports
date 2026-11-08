$NetBSD$

Relocate prefix-owned runtime defaults using the loaded shared library.
Preserve upstream platform fixes and explicit caller configuration.
Origin: pkgsrc and EmberBSD contributors (AI-assisted).

--- src/fcinit.c.orig
+++ src/fcinit.c
@@ -36,42 +36,83 @@
 #  pragma message("To suppress these warnings, define FC_NO_MT.")
 #endif
 
+/* Only compiled default paths enter this builder. User XML is unchanged. */
+static void
+FcInitFallbackPath (FcStrBuf *xml, const char *tag, const char *attributes,
+                    const char *path)
+{
+    FcChar8 *relocated = FcConfigRelocatePath ((const FcChar8 *)path);
+    const FcChar8 *p;
+
+    if (!relocated) {
+        xml->failed = FcTrue;
+        return;
+    }
+    FcStrBufFormat (xml, "<%s%s>", tag, attributes);
+    for (p = relocated; *p; p++) {
+        const char *escaped = *p == '&' ? "&amp;" :
+                              *p == '<' ? "&lt;" :
+                              *p == '>' ? "&gt;" : NULL;
+        if (escaped)
+            FcStrBufString (xml, (const FcChar8 *)escaped);
+        else
+            FcStrBufChar (xml, *p);
+    }
+    FcStrBufFormat (xml, "</%s>", tag);
+    FcStrFree (relocated);
+}
+
 static FcConfig *
 FcInitFallbackConfig (const FcChar8 *sysroot)
 {
-    FcConfig      *config;
-    const FcChar8 *fallback = (const FcChar8 *)
-	""
-	"<fontconfig>" FC_DEFAULT_FONTS
-	"  <dir prefix=\"xdg\">fonts</dir>"
-	"  <cachedir>" FC_CACHEDIR
-	"</cachedir>"
-	"  <cachedir prefix=\"xdg\">fontconfig</cachedir>"
-	"  <include ignore_missing=\"yes\">" CONFIGDIR
-	"</include>"
-	"  <include ignore_missing=\"yes\" prefix=\"xdg\">fontconfig/conf.d</include>"
-	"  <include ignore_missing=\"yes\" prefix=\"xdg\">fontconfig/fonts.conf</include>"
-	"</fontconfig>";
+    FcConfig *config;
+    const char *fonts[] = FC_DEFAULT_FONT_DIRS;
+    const char **font;
+    FcStrBuf xml;
+    FcChar8 *fallback;
+
+    FcStrBufInit (&xml, NULL, 0);
+    FcStrBufString (&xml, (const FcChar8 *)"<fontconfig>");
+    for (font = fonts; *font; font++)
+        FcInitFallbackPath (&xml, "dir", "", *font);
+    FcStrBufString (&xml, (const FcChar8 *)"<dir prefix=\"xdg\">fonts</dir>");
+    FcInitFallbackPath (&xml, "cachedir", "", FC_CACHEDIR);
+    FcStrBufString (&xml, (const FcChar8 *)"<cachedir prefix=\"xdg\">fontconfig</cachedir>");
+    FcInitFallbackPath (&xml, "include", " ignore_missing=\"yes\"", CONFIGDIR);
+    FcStrBufString (&xml, (const FcChar8 *)
+        "<include ignore_missing=\"yes\" prefix=\"xdg\">fontconfig/conf.d</include>"
+        "<include ignore_missing=\"yes\" prefix=\"xdg\">fontconfig/fonts.conf</include>"
+        "</fontconfig>");
+    fallback = FcStrBufDone (&xml);
+    if (!fallback)
+        return NULL;
 
     config = FcConfigCreate();
     if (!config)
-	goto bail0;
+        goto bail0;
     FcConfigSetSysRoot (config, sysroot);
     if (!FcConfigParseAndLoadFromMemory (config, fallback, FcFalse))
-	goto bail1;
-
+        goto bail1;
+
+    FcStrFree (fallback);
     return config;
 
 bail1:
     FcConfigDestroy (config);
 bail0:
-    return 0;
+    FcStrFree (fallback);
+    return NULL;
 }
 
 static FcConfig *
 FcInitFallbackConfigWithFilter (FcConfig *config, const FcChar8 *sysroot)
 {
     FcConfig *fallback = FcInitFallbackConfig (sysroot);
+
+    if (!fallback) {
+        FcConfigDestroy (config);
+        return NULL;
+    }
 
     /* Copy filter data */
     fallback->filter_func = config->filter_func;
@@ -114,14 +155,25 @@
 
 	return fallback;
     }
-    (void)FcConfigParseOnly (config, (const FcChar8 *)FC_TEMPLATEDIR, FcFalse);
+    {
+        FcChar8 *templates = FcConfigRelocatePath ((const FcChar8 *)FC_TEMPLATEDIR);
+        if (!templates) {
+            FcConfigDestroy (config);
+            return NULL;
+        }
+        (void)FcConfigParseOnly (config, templates, FcFalse);
+        FcStrFree (templates);
+    }
 
     if (config->cacheDirs && config->cacheDirs->num == 0) {
-	FcChar8 *prefix, *p;
+	FcChar8 *prefix = NULL, *p;
+        FcChar8 *cache = FcConfigRelocatePath ((const FcChar8 *)FC_CACHEDIR);
 	size_t   plen;
 	FcBool   have_own = FcFalse;
 	char    *env_file, *env_path;
 
+        if (!cache)
+            goto bail;
 	env_file = getenv ("FONTCONFIG_FILE");
 	env_path = getenv ("FONTCONFIG_PATH");
 	if ((env_file != NULL && env_file[0] != 0) ||
@@ -133,7 +185,7 @@
 	             "Fontconfig warning: no <cachedir> elements found. Check configuration.\n");
 	    fprintf (stderr,
 	             "Fontconfig warning: adding <cachedir>%s</cachedir>\n",
-	             FC_CACHEDIR);
+	             cache);
 	}
 	prefix = FcConfigXdgCacheHome();
 	if (!prefix)
@@ -149,7 +201,7 @@
 	    fprintf (stderr,
 	             "Fontconfig warning: adding <cachedir prefix=\"xdg\">fontconfig</cachedir>\n");
 
-	if (!FcConfigAddCacheDir (config, (FcChar8 *)FC_CACHEDIR) ||
+	if (!FcConfigAddCacheDir (config, cache) ||
 	    !FcConfigAddCacheDir (config, (FcChar8 *)prefix)) {
 	    FcConfig      *fallback;
 	    const FcChar8 *sysroot;
@@ -160,11 +212,13 @@
 	             "Fontconfig error: out of memory");
 	    if (prefix)
 		FcStrFree (prefix);
+            FcStrFree (cache);
 	    fallback = FcInitFallbackConfigWithFilter (config, sysroot);
 
 	    return fallback;
 	}
 	FcStrFree (prefix);
+        FcStrFree (cache);
     }
 
     return config;
