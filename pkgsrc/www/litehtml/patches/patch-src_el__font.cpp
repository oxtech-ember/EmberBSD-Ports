$NetBSD$

Include the standard declaration for std::atoi.

--- litehtml/src/el_font.cpp.orig
+++ litehtml/src/el_font.cpp
@@ -1,3 +1,5 @@
+#include <cstdlib>
+
 #include "el_font.h"
 #include "document.h"
 
@@ -23,7 +25,7 @@
     str = get_attr("size");
     if(str)
     {
-        int sz = atoi(str);
+        int sz = std::atoi(str);
         if(*str == '+' || *str == '-')
         {
             sz = 3 + std::max(-7, std::min(sz, 7)); // relative size
