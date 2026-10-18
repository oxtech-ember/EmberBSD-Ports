$NetBSD$

Origin: EmberBSD (AI-assisted).
The thread-local value is an array of structures, not an array of pointers.
Use the actual element address when the thread destructor releases the array.
Local change. Not submitted upstream.

--- libgjs-private/gjs-util.c.orig
+++ libgjs-private/gjs-util.c
@@ -85,10 +85,10 @@ static size_t get_number_of_locale_categories(void) {
     return __builtin_popcount(LC_ALL_MASK) + 1;
 }
 
-static void gjs_locales_free(GjsLocale** locales) {
+static void gjs_locales_free(GjsLocale* locales) {
     size_t number_of_categories = get_number_of_locale_categories();
     for (size_t i = 0; i < number_of_categories; i++) {
-        GjsLocale* locale = locales[i];
+        GjsLocale* locale = &locales[i];
         gjs_clear_locale_id(&locale->id);
         g_clear_pointer(&locale->name, g_free);
         g_clear_pointer(&locale->prior_name, g_free);
