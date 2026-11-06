$NetBSD$

Resolve prefix-owned default paths after relocation.
Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- /dev/null
+++ include/X11/XlibRelocate.h
@@ -0,0 +1,111 @@
+/* SPDX-License-Identifier: MIT */
+/* Copyright (c) 2026 EmberBSD contributors. */
+/* Private build-time helper shared by libX11 and its libXt consumer. */
+#ifndef XLIB_RELOCATE_PRIVATE_H
+#define XLIB_RELOCATE_PRIVATE_H
+#include <stddef.h>
+#include <stdlib.h>
+#if defined(X11_RELOC_HAVE_DLADDR) && !defined(_WIN32)
+#include <dlfcn.h>
+#include <limits.h>
+#include <string.h>
+
+/* Normalize absolute paths lexically without requiring target files to exist. */
+static char *
+_x11_reloc_normalize(const char *input)
+{
+    char *result, *p, *save = NULL, *part, *copy;
+    size_t used = 1;
+    if (!input || *input != '/') return NULL;
+    /* Xt substitutions are expanded later; never simplify a template's .. */
+    if (strchr(input, '%')) {
+        const char *component = input;
+        while (*component) {
+            const char *end;
+            while (*component == '/') ++component;
+            end = strchr(component, '/');
+            if (!end) end = component + strlen(component);
+            if (end - component == 2 && component[0] == '.' && component[1] == '.')
+                return NULL;
+            component = end;
+        }
+    }
+    if (!(copy = strdup(input))) return NULL;
+    result = malloc(strlen(input) + 2);
+    if (!result) { free(copy); return NULL; }
+    result[0] = '/'; result[1] = '\0';
+    for (part = strtok_r(copy, "/", &save); part; part = strtok_r(NULL, "/", &save)) {
+        size_t n;
+        if (!strcmp(part, ".")) continue;
+        if (!strcmp(part, "..")) {
+            if (used > 1) {
+                p = strrchr(result, '/');
+                used = p == result ? 1 : (size_t)(p - result);
+                result[used] = '\0';
+            }
+            continue;
+        }
+        if (used > 1) result[used++] = '/';
+        n = strlen(part); memcpy(result + used, part, n); used += n; result[used] = '\0';
+    }
+    free(copy); return result;
+}
+
+/* Returns malloc-owned moved path or NULL to preserve the configured fallback.
+ * Only known installed shared-library anchors and prefix-owned paths qualify. */
+static char *
+_x11_relocated_path(const void *anchor, const char *library,
+                    const char *configured_prefix, const char *configured_libdir,
+                    const char *configured_path)
+{
+    Dl_info info;
+    char real[PATH_MAX], *prefix = NULL, *libdir = NULL, *path = NULL;
+    char *actual_dir, *name, *out = NULL;
+    size_t plen, rlen, dlen, baselen;
+    const char *rel;
+    if (!dladdr(anchor, &info) || !info.dli_fname || !realpath(info.dli_fname, real))
+        return NULL;
+    actual_dir = strrchr(real, '/');
+    if (!actual_dir) return NULL;
+    name = actual_dir + 1; baselen = strlen(library);
+    {
+        const char *suffix;
+        size_t n = strlen(name);
+        if (strncmp(name, library, baselen) || name[baselen] != '.') return NULL;
+        suffix = name + baselen;
+        if (!(n >= 6 && !strcmp(name + n - 6, ".dylib")) &&
+            !(strncmp(suffix, ".so", 3) == 0 && (suffix[3] == '\0' || suffix[3] == '.')))
+            return NULL;
+    }
+    *actual_dir = '\0';
+    prefix = _x11_reloc_normalize(configured_prefix);
+    libdir = _x11_reloc_normalize(configured_libdir);
+    path = _x11_reloc_normalize(configured_path);
+    if (!prefix || !libdir || !path) goto done;
+    plen = strlen(prefix);
+    if (plen <= 1 || strncmp(libdir, prefix, plen) || libdir[plen] != '/' ||
+        strncmp(path, prefix, plen) || path[plen] != '/') goto done;
+    rel = libdir + plen + 1; rlen = strlen(rel); dlen = strlen(real);
+    if (!rlen || dlen < rlen + 1 || real[dlen-rlen-1] != '/' ||
+        strcmp(real+dlen-rlen, rel)) goto done;
+    real[dlen-rlen-1] = '\0';
+    out = malloc(strlen(real) + strlen(path + plen + 1) + 2);
+    if (out) {
+        size_t n = strlen(real);
+        memcpy(out, real, n);
+        out[n++] = '/';
+        strcpy(out + n, path + plen + 1);
+    }
+done:
+    free(prefix); free(libdir); free(path); return out;
+}
+#else
+static char *
+_x11_relocated_path(const void *anchor, const char *library,
+                    const char *prefix, const char *libdir, const char *path)
+{
+    (void)anchor; (void)library; (void)prefix; (void)libdir; (void)path;
+    return NULL;
+}
+#endif
+#endif
