$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Bound formatting and check truncation in the tutorial.
--- example/tutorial/tutorial.cpp
+++ example/tutorial/tutorial.cpp
@@ -122,8 +122,10 @@
     Value author;
     {
         char buffer2[10];
-        int len = sprintf(buffer2, "%s %s", "Milo", "Yip");  // synthetic example of dynamically created string.
+        int len = snprintf(buffer2, sizeof(buffer2), "%s %s", "Milo", "Yip");  // synthetic example of dynamically created string.
 
+        if (len < 0 || static_cast<size_t>(len) >= sizeof(buffer2))
+            return 1;
         author.SetString(buffer2, static_cast<SizeType>(len), document.GetAllocator());
         // Shorter but slower version:
         // document["hello"].SetString(buffer, document.GetAllocator());
