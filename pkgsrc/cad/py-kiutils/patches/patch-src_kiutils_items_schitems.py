$NetBSD$

Keep the parsed junction diameter separate from its color. Otherwise a nonzero
diameter is lost, and a diameter token following the color breaks serialization.

--- src/kiutils/items/schitems.py.orig
+++ src/kiutils/items/schitems.py
@@ -68,7 +68,7 @@
         for item in exp:
             if item[0] == 'at': object.position = Position().from_sexpr(item)
             if item[0] == 'color': object.color = ColorRGBA().from_sexpr(item)
-            if item[0] == 'diameter': object.color = item[1]
+            if item[0] == 'diameter': object.diameter = item[1]
             if item[0] == 'uuid': object.uuid = item[1]
         return object
 
