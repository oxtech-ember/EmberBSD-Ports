$NetBSD$

Include the standard declaration for std::atoi.

--- src/el_font.cpp.orig
+++ src/el_font.cpp
@@ -1,3 +1,5 @@
+#include <cstdlib>
+
 #include "el_font.h"
 #include "document.h"
 
@@ -24,7 +26,7 @@ void litehtml::el_font::parse_attributes()
 	str = get_attr("size");
 	if(str)
 	{
-		int sz = atoi(str);
+		int sz = std::atoi(str);
 		if(*str == '+' || *str == '-') sz = 3 + sz; // relative size
 
 		if(sz <= 1)
