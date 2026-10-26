# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
# Keep source initialization strict while allowing streamed Clang header locations.

--- lib/tokenlist.cpp.orig
+++ lib/tokenlist.cpp
@@ -102,7 +102,10 @@
     if (it != mFiles.cend())
         return static_cast<int>(std::distance(mFiles.cbegin(), it));
 
-    assert(mTokensFrontBack->front == nullptr); // has no effect if tokens have already been created
+    // Establish the source file before creating tokens. Clang import may
+    // discover headers later; appending their names preserves existing file
+    // indices and the language fixed by the TokenList constructor.
+    assert(!mFiles.empty() || mTokensFrontBack->front == nullptr);
 
     // The "mFiles" vector remembers what files have been tokenized..
     mFiles.push_back(std::move(fileName));
