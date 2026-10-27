$NetBSD$

Accept equal absolute symbols with value zero. Keep unknown bitcode
offsets separate from known ELF offsets.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- ELF/InputFiles.cpp.orig
+++ ELF/InputFiles.cpp
@@ -1943,7 +1943,7 @@
     int c = irSym.getComdatIndex();
     if (c != -1 && !keptComdats[c])
       continue;
-    reportDuplicate(ctx, sym, this, nullptr, 0);
+    reportDuplicate(ctx, sym, this, nullptr, std::nullopt);
   }
 }
 
