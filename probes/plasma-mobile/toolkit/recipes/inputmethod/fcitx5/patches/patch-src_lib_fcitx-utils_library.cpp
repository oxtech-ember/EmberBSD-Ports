$NetBSD: patch-src_lib_fcitx-utils_library.cpp,v 1.1 2022/03/27 12:45:04 tnn Exp $

Fix build on SunOS.

Reject a missing file-data signature before advancing the pointer or calling
its parser. Keep the common munmap path for failed searches.
This additional fix is EmberBSD work (AI-assisted), not submitted upstream.

--- src/lib/fcitx-utils/library.cpp.orig
+++ src/lib/fcitx-utils/library.cpp
@@ -105,7 +105,7 @@
         flag |= RTLD_GLOBAL;
     }
 
-#ifdef HAS_DLMOPEN
+#if defined(HAS_DLMOPEN) && defined(LM_ID_NEWLM)
     if (hint & LibraryLoadHint::NewNameSpace) {
         // allow dlopen self
         d->handle_ = dlmopen(
@@ -203,12 +203,13 @@
         const char *pos = stringutils::backwardSearch(
             static_cast<char *>(data), static_cast<size_t>(statbuf.st_size),
             magic, lenOfMagic, 0);
-        pos += lenOfMagic;
-
-        if (parser) {
-            parser(pos);
+        if (pos) {
+            pos += lenOfMagic;
+            if (parser) {
+                parser(pos);
+            }
+            result = true;
         }
-        result = true;
 #ifdef HAVE_SYS_MMAN_H
         if (needunmap) {
             munmap(needunmap, statbuf.st_size);
@@ -225,7 +226,7 @@
 }
 
 bool Library::isNewNamespaceSupported() {
-#ifdef HAS_DLMOPEN
+#if defined(HAS_DLMOPEN) && defined(LM_ID_NEWLM)
     return true;
 #else
     return false;
