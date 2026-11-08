$NetBSD$

Relocate prefix-owned runtime defaults using the loaded shared library.
Preserve upstream platform fixes and explicit caller configuration.
Origin: pkgsrc and EmberBSD contributors (AI-assisted).

--- src/fccfg.c.orig
+++ src/fccfg.c
@@ -31,6 +31,73 @@
 #  include <dirent.h>
 #endif
 #include <sys/types.h>
+#ifdef FC_HAVE_DLADDR
+#  include <dlfcn.h>
+#endif
+
+#ifdef FC_HAVE_DLADDR
+static const char fcLibraryAnchor;
+#endif
+
+/* Relocate only compiled defaults owned by the configured prefix. Never apply
+ * this to environment overrides or paths supplied by configuration files. */
+FcChar8 *
+FcConfigRelocatePath (const FcChar8 *path)
+{
+#ifdef FC_HAVE_DLADDR
+    const char *prefix = FC_INSTALL_PREFIX;
+    const char *libdir = FC_INSTALL_LIBDIR;
+    size_t plen = strlen (prefix);
+    Dl_info image;
+    const char *base, *suffix;
+    char *resolved, *slash;
+    size_t len, slen;
+    FcStrBuf result;
+
+    if (plen <= 1 || strncmp ((const char *)path, prefix, plen) != 0 ||
+        (path[plen] != '/' && path[plen] != '\0') ||
+        strncmp (libdir, prefix, plen) != 0 || libdir[plen] != '/')
+        return FcStrCopy (path);
+    if (!dladdr (&fcLibraryAnchor, &image) || !image.dli_fname)
+        return FcStrCopy (path);
+    base = strrchr (image.dli_fname, '/');
+    base = base ? base + 1 : image.dli_fname;
+    len = strlen (base);
+    if (!(strcmp (base, "libfontconfig.so") == 0 ||
+          strncmp (base, "libfontconfig.so.", sizeof ("libfontconfig.so.") - 1) == 0 ||
+          (strncmp (base, "libfontconfig.", sizeof ("libfontconfig.") - 1) == 0 &&
+           len >= sizeof ("libfontconfig.dylib") - 1 &&
+           strcmp (base + len - 6, ".dylib") == 0)))
+        return FcStrCopy (path); /* A static executable is not a library. */
+
+    resolved = realpath (image.dli_fname, NULL);
+    if (!resolved)
+        return NULL;
+    slash = strrchr (resolved, '/');
+    if (!slash) {
+        free (resolved);
+        return NULL;
+    }
+    *slash = '\0';
+    suffix = libdir + plen;
+    slen = strlen (suffix);
+    len = strlen (resolved);
+    if (len < slen || strcmp (resolved + len - slen, suffix) != 0) {
+        free (resolved);
+        return FcStrCopy (path); /* Preserve explicitly different layouts. */
+    }
+    resolved[len - slen] = '\0';
+    FcStrBufInit (&result, NULL, 0);
+    FcStrBufString (&result, (const FcChar8 *)resolved);
+    FcStrBufString (&result, path + plen);
+    if (result.len == 0)
+        FcStrBufChar (&result, '/');
+    free (resolved);
+    return FcStrBufDone (&result);
+#else
+    return FcStrCopy (path);
+#endif
+}
 
 #if defined(_WIN32) && !defined(R_OK)
 #  define R_OK 4
@@ -2357,7 +2424,6 @@
 {
     FcChar8 **path;
     FcChar8  *env, *e, *colon;
-    FcChar8  *dir;
     int       npath;
     int       i;
 
@@ -2405,11 +2471,9 @@
 	strcat ((char *)fontconfig_path, "\\fonts");
     }
 #endif
-    dir = (FcChar8 *)FONTCONFIG_PATH;
-    path[i] = malloc (strlen ((char *)dir) + 1);
+    path[i] = FcConfigRelocatePath ((const FcChar8 *)FONTCONFIG_PATH);
     if (!path[i])
 	goto bail1;
-    strcpy ((char *)path[i], (const char *)dir);
     return path;
 
 bail1:
