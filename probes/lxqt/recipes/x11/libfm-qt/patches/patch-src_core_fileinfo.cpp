$NetBSD$

Do not compare an absent optional GIO content type.
Keep an existing file mode and leave an unknown special mode unset.

--- src/core/fileinfo.cpp.orig
+++ src/core/fileinfo.cpp
@@ -95,7 +95,7 @@
         case G_FILE_TYPE_MOUNTABLE:
             break;
         case G_FILE_TYPE_SPECIAL:
-            if(mode_) {
+            if(!tmp) {
                 break;
             }
             /* if it's a special file but it doesn't have UNIX mode, compose a fake one. */
