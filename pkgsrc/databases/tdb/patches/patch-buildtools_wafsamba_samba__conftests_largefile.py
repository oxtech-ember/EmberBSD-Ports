$NetBSD$

Origin: EmberBSD (AI-assisted).

Upstream status: not submitted.

Test off_t width at compile time without executing a target program.

--- buildtools/wafsamba/samba_conftests.py.orig
+++ buildtools/wafsamba/samba_conftests.py
@@ -88,9 +88,9 @@
     '''see what we need for largefile support'''
     getconf_cflags = conf.CHECK_COMMAND(['getconf', 'LFS_CFLAGS'])
     if getconf_cflags is not False:
-        if (conf.CHECK_CODE('if (sizeof(off_t) < 8) return 1',
+        if (conf.CHECK_CODE('(void)sizeof(char[(sizeof(off_t) >= 8) ? 1 : -1])',
                             define='WORKING_GETCONF_LFS_CFLAGS',
-                            execute=True,
+                            execute=False,
                             cflags=getconf_cflags,
                             msg='Checking getconf large file support flags work')):
             conf.ADD_CFLAGS(getconf_cflags)
@@ -103,23 +103,23 @@
                     else:
                         conf.DEFINE(str(flag_split[0]), str(flag_split[1]))
 
-    if conf.CHECK_CODE('if (sizeof(off_t) < 8) return 1',
+    if conf.CHECK_CODE('(void)sizeof(char[(sizeof(off_t) >= 8) ? 1 : -1])',
                        define,
-                       execute=True,
+                       execute=False,
                        msg='Checking for large file support without additional flags'):
         return True
 
-    if conf.CHECK_CODE('if (sizeof(off_t) < 8) return 1',
+    if conf.CHECK_CODE('(void)sizeof(char[(sizeof(off_t) >= 8) ? 1 : -1])',
                        define,
-                       execute=True,
+                       execute=False,
                        cflags='-D_FILE_OFFSET_BITS=64',
                        msg='Checking for -D_FILE_OFFSET_BITS=64'):
         conf.DEFINE('_FILE_OFFSET_BITS', 64)
         return True
 
-    if conf.CHECK_CODE('if (sizeof(off_t) < 8) return 1',
+    if conf.CHECK_CODE('(void)sizeof(char[(sizeof(off_t) >= 8) ? 1 : -1])',
                        define,
-                       execute=True,
+                       execute=False,
                        cflags='-D_LARGE_FILES',
                        msg='Checking for -D_LARGE_FILES'):
         conf.DEFINE('_LARGE_FILES', 1)
