$NetBSD$

Origin: EmberBSD (AI-assisted).

Upstream status: not submitted.

Allow consumers to request only uname fields they actually use.

--- buildtools/wafsamba/samba_conftests.py.orig
+++ buildtools/wafsamba/samba_conftests.py
@@ -439,10 +439,10 @@
 
 
 @conf
-def CHECK_UNAME(conf):
+def CHECK_UNAME(conf, fields=('sysname', 'machine', 'release', 'version')):
     '''setup SYSTEM_UNAME_* defines'''
     ret = True
-    for v in "sysname machine release version".split():
+    for v in fields:
         if not conf.CHECK_CODE('''
                                int printf(const char *format, ...);
                                struct utsname n;
