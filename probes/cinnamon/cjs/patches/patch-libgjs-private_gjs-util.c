$NetBSD$

NetBSD provides newlocale(3) and duplocale(3) but not uselocale(3).
Add a compat wrapper so gjs_set_thread_locale compiles; per-thread
switching degrades to the process-global locale (recorded boundary
for the Cinnamon Wayland session port).

--- libgjs-private/gjs-util.c.orig
+++ libgjs-private/gjs-util.c
@@ -26,6 +26,20 @@
 } GjsLocale;
 
 #define UNSET_LOCALE_ID ((locale_t)0)
+
+/* EmberBSD (NetBSD): the platform has newlocale(3)/duplocale(3) but no
+ * uselocale(3). Per-thread locale switching degrades to the
+ * process-global locale; the query form reports the global locale.
+ * newlocale(3) results are kept for the stored ids, so the data flow
+ * above stays intact. */
+#if defined(__NetBSD__) && !defined(GJS_HAVE_USELOCALE)
+#  define GJS_USELOCALE_COMPAT 1
+static locale_t gjs_compat_uselocale(locale_t newloc) {
+    (void)newloc;
+    return LC_GLOBAL_LOCALE;
+}
+#  define uselocale gjs_compat_uselocale
+#endif
 
 static void gjs_clear_locale_id(locale_t* id) {
     if (id == NULL)
