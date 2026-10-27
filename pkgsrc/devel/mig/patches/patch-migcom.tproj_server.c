$NetBSD$

Use selected native tools.

--- migcom.tproj/server.c.orig
+++ migcom.tproj/server.c
@@ -73,7 +73,7 @@
 #define __KernelServer_unreachable() \
 do {\
   if (UseMachMsg2) \
-    fatal("mach_msg2 KernelServer support for this code block is unimplemented."); \   
+    fatal("mach_msg2 KernelServer support for this code block is unimplemented."); \
 } while (0)
 
 static void
