$NetBSD$

Reject truncated property values and release keys on invalid references (EmberBSD, AI-assisted).

--- code/OpenDDLParser.cpp.orig
+++ code/OpenDDLParser.cpp
@@ -892,6 +892,10 @@
             ++in;
             in = getNextToken(in, end);
             Value *primData(nullptr);
+            if (in == end) {
+                delete id;
+                return in;
+            }
             if (isInteger(in, end)) {
                 in = parseIntegerLiteral(in, end, &primData);
                 createPropertyWithData(id, primData, prop);
@@ -910,7 +914,8 @@
                     (*prop)->m_ref = ref;
                 }
             }
-        } else {
+        }
+        if (nullptr == *prop) {
             delete id;
         }
     }
