$NetBSD: patch-gmodule_gmodule.c,v 1.4 2024/10/22 09:50:39 adam Exp $

RTL_GLOBAL is a bug.
https://gitlab.gnome.org/GNOME/glib/-/merge_requests/2171

--- gmodule/gmodule.c.orig
+++ gmodule/gmodule.c
@@ -498,9 +498,8 @@
       if (!main_module)
 	{
 	  handle = _g_module_self ();
-/* On Android 64 bit, RTLD_DEFAULT is (void *)0x0
- * so it always fails to create main_module if file_name is NULL */
-#if !defined(__ANDROID__) || !defined(__LP64__)
+/* On Linux, handle == RTLD_DEFAULT is (void *)0x0 */
+#if G_MODULE_IMPL != G_MODULE_IMPL_DL
 	  if (handle)
 #endif
 	    {
