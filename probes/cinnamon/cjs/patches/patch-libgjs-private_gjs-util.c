$NetBSD$

Do not report per-thread locale selection as successful when the target libc
does not implement uselocale(3). Keep the query operation available and return
ENOTSUP when a caller requests a per-thread locale. Also pass the locale array
itself to its GLib thread-data destructor.

--- libgjs-private/gjs-util.c.orig
+++ libgjs-private/gjs-util.c
@@ -19,6 +19,7 @@
 #include "libgjs-private/gjs-util.h"
 #include "util/console.h"
 
+#if !defined(EMBERBSD_NO_USELOCALE)
 typedef struct {
     locale_t id;
     char* name;
@@ -88,7 +89,7 @@
-static void gjs_locales_free(GjsLocale** locales) {
+static void gjs_locales_free(GjsLocale* locales) {
     size_t number_of_categories = get_number_of_locale_categories();
     for (size_t i = 0; i < number_of_categories; i++) {
-        GjsLocale* locale = locales[i];
+        GjsLocale* locale = &locales[i];
         gjs_clear_locale_id(&locale->id);
         g_clear_pointer(&locale->name, g_free);
         g_clear_pointer(&locale->prior_name, g_free);
@@ -104,4 +105,5 @@
 
 static GPrivate gjs_private_locale_key =
     G_PRIVATE_INIT((GDestroyNotify)gjs_locales_free);
+#endif
 
@@ -115,5 +117,12 @@
 const char* gjs_set_thread_locale(GjsLocaleCategory category,
                                   const char* locale_name) {
+#if defined(EMBERBSD_NO_USELOCALE)
+    if (locale_name == NULL)
+        return setlocale(category, NULL);
+
+    errno = ENOTSUP;
+    return NULL;
+#else
     locale_t new_locale_id = UNSET_LOCALE_ID, old_locale_id = UNSET_LOCALE_ID;
     char* prior_name = NULL;
     bool success = false;
@@ -172,5 +181,6 @@
     if (!success)
         return NULL;
 
     return locale->prior_name;
+#endif
 }
