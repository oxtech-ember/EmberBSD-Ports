$NetBSD$

Origin: EmberBSD (AI-assisted).
Upstream status: not submitted.

Use the selected Python interpreter for cached cross answers instead of
implicitly selecting the host shell. Pass answer text as an argument.

--- buildtools/wafsamba/samba_cross.py.orig
+++ buildtools/wafsamba/samba_cross.py
@@ -134,7 +134,9 @@
                 cross_answers_incomplete = True
                 add_answer(ca_file, msg, ans)
             (retcode, retstring) = ans
-            args = ['/bin/sh', '-c', "printf %%s '%s'; exit %d" % (retstring, retcode)]
+            args = [sys.executable, '-B', '-E', '-S', '-c',
+                    'import sys; sys.stdout.write(sys.argv[1]); sys.exit(int(sys.argv[2]))',
+                    retstring, str(retcode)]
         real_Popen.__init__(*(obj, args), **kw)
 
 
