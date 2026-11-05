$NetBSD$

Resolve installed default paths from the actual component location.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- /dev/null
+++ girepository/gi-relocate-private.h
@@ -0,0 +1,71 @@
+/* SPDX-License-Identifier: LGPL-2.0-or-later */
+/* Private installed-path resolver. Unknown/static layouts keep configured paths. */
+#pragma once
+#include "gi-relocate-config.h"
+#if defined(GI_HAVE_DLADDR) && !defined(G_OS_WIN32)
+#include <dlfcn.h>
+#include <limits.h>
+#include <stdlib.h>
+#include <string.h>
+
+static char *
+_g_ir_relocated_path (const void *anchor, const char *configured)
+{
+  Dl_info info;
+  char resolved[PATH_MAX];
+  g_autofree char *base = NULL;
+  g_autofree char *dir = NULL;
+  g_autofree char *prefix = NULL;
+  g_autofree char *configured_prefix = NULL;
+  g_autofree char *canonical_layout = NULL;
+  g_autofree char *canonical_target = NULL;
+  const char *layout, *relative, *end;
+  gsize len, plen;
+
+  if (!dladdr (anchor, &info) || !info.dli_fname ||
+      !realpath (info.dli_fname, resolved))
+    return NULL;
+  base = g_path_get_basename (resolved);
+  if (g_str_equal (base, "g-ir-compiler") || g_str_equal (base, "g-ir-generate"))
+    layout = GI_RELOC_BINDIR;
+  else if ((g_str_has_prefix (base, "libgirepository-1.0.") &&
+            g_str_has_suffix (base, ".dylib")) ||
+           g_str_equal (base, "libgirepository-1.0.so") ||
+           g_str_has_prefix (base, "libgirepository-1.0.so."))
+    layout = GI_RELOC_LIBDIR;
+  else
+    return NULL;
+
+  if (!g_path_is_absolute (GI_RELOC_PREFIX) ||
+      !g_path_is_absolute (layout) || !g_path_is_absolute (configured))
+    return NULL;
+  /* Compare normalized complete paths, so dot components cannot escape the
+   * configured prefix or turn a sibling prefix into a match. */
+  configured_prefix = g_canonicalize_filename (GI_RELOC_PREFIX, NULL);
+  canonical_layout = g_canonicalize_filename (layout, NULL);
+  canonical_target = g_canonicalize_filename (configured, NULL);
+  plen = strlen (configured_prefix);
+  if (!g_str_has_prefix (canonical_layout, configured_prefix) || canonical_layout[plen] != '/' ||
+      !g_str_has_prefix (canonical_target, configured_prefix) || canonical_target[plen] != '/')
+    return NULL;
+  relative = canonical_layout + plen + 1;
+  if (!*relative)
+    return NULL;
+  dir = g_path_get_dirname (resolved);
+  len = strlen (dir);
+  end = dir + len;
+  if (len <= strlen (relative) || end[-(gssize)strlen (relative)-1] != '/' ||
+      strcmp (end - strlen (relative), relative) != 0)
+    return NULL;
+  prefix = g_strndup (dir, len - strlen (relative) - 1);
+  return g_build_filename (*prefix ? prefix : G_DIR_SEPARATOR_S, canonical_target + plen + 1, NULL);
+}
+#else
+static char *
+_g_ir_relocated_path (const void *anchor, const char *configured)
+{
+  (void) anchor;
+  (void) configured;
+  return NULL;
+}
+#endif
