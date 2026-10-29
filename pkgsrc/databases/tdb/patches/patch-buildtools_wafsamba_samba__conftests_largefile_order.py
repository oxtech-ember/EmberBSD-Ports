$NetBSD$

Origin: EmberBSD (AI-assisted). Upstream status: not submitted.

Use compile-time target ABI checks before optional target getconf.

--- buildtools/wafsamba/samba_conftests.py.orig
+++ buildtools/wafsamba/samba_conftests.py
@@ -86,6 +86,34 @@
 @conf
 def CHECK_LARGEFILE(conf, define='HAVE_LARGEFILE'):
     '''see what we need for largefile support'''
+    def check_compile_flags():
+        if conf.CHECK_CODE('(void)sizeof(char[(sizeof(off_t) >= 8) ? 1 : -1])',
+                           define,
+                           execute=False,
+                           msg='Checking for large file support without additional flags'):
+            return True
+
+        if conf.CHECK_CODE('(void)sizeof(char[(sizeof(off_t) >= 8) ? 1 : -1])',
+                           define,
+                           execute=False,
+                           cflags='-D_FILE_OFFSET_BITS=64',
+                           msg='Checking for -D_FILE_OFFSET_BITS=64'):
+            conf.DEFINE('_FILE_OFFSET_BITS', 64)
+            return True
+
+        if conf.CHECK_CODE('(void)sizeof(char[(sizeof(off_t) >= 8) ? 1 : -1])',
+                           define,
+                           execute=False,
+                           cflags='-D_LARGE_FILES',
+                           msg='Checking for -D_LARGE_FILES'):
+            conf.DEFINE('_LARGE_FILES', 1)
+            return True
+        return False
+
+
+    if conf.env.CROSS_COMPILE and check_compile_flags():
+        return True
+
     getconf_cflags = conf.CHECK_COMMAND(['getconf', 'LFS_CFLAGS'])
     if getconf_cflags is not False:
         if (conf.CHECK_CODE('(void)sizeof(char[(sizeof(off_t) >= 8) ? 1 : -1])',
@@ -103,29 +131,7 @@
                     else:
                         conf.DEFINE(str(flag_split[0]), str(flag_split[1]))
 
-    if conf.CHECK_CODE('(void)sizeof(char[(sizeof(off_t) >= 8) ? 1 : -1])',
-                       define,
-                       execute=False,
-                       msg='Checking for large file support without additional flags'):
-        return True
-
-    if conf.CHECK_CODE('(void)sizeof(char[(sizeof(off_t) >= 8) ? 1 : -1])',
-                       define,
-                       execute=False,
-                       cflags='-D_FILE_OFFSET_BITS=64',
-                       msg='Checking for -D_FILE_OFFSET_BITS=64'):
-        conf.DEFINE('_FILE_OFFSET_BITS', 64)
-        return True
-
-    if conf.CHECK_CODE('(void)sizeof(char[(sizeof(off_t) >= 8) ? 1 : -1])',
-                       define,
-                       execute=False,
-                       cflags='-D_LARGE_FILES',
-                       msg='Checking for -D_LARGE_FILES'):
-        conf.DEFINE('_LARGE_FILES', 1)
-        return True
-    return False
-
+    return check_compile_flags()
 
 @conf
 def CHECK_C_PROTOTYPE(conf, function, prototype, define, headers=None, msg=None, lib=None):
