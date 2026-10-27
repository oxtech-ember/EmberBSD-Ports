$NetBSD$

Match the native FSPathMakeRef path parameter type.

--- setfflags/setfflags.c.orig
+++ setfflags/setfflags.c
@@ -225,7 +225,7 @@
   pFlags = (i == 1) ? kFolderOnlyFlags : kFinderFlags;
 
   // get file reference from path
-  if ((err = FSPathMakeRef(fileStr, &fileRef, NULL)) != noErr)
+  if ((err = FSPathMakeRef((const UInt8 *)fileStr, &fileRef, NULL)) != noErr)
   {
     if (!silentMode)
       fprintf(stderr, "FSPathMakeRef: Error %d for file %s\n", err, fileStr);
@@ -316,7 +316,7 @@
   pFlags = (i == 1) ? kFolderOnlyFlags : kFinderFlags;
 
   //get file reference from path
-  err = FSPathMakeRef(fileStr, &fileRef, NULL);
+  err = FSPathMakeRef((const UInt8 *)fileStr, &fileRef, NULL);
   if (err != noErr)
   {
     if (!silentMode)
