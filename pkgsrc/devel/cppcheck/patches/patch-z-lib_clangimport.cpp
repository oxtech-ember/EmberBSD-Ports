# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
# Recognize unnamed parameter source coordinates in the Clang AST.

--- lib/clangimport.cpp.orig
+++ lib/clangimport.cpp
@@ -436,6 +436,17 @@
         return "";
     if (startsWith(str,"<invalid"))
         return "";
+    if (nodeType == ParmVarDecl) {
+        const std::size_t col = str.rfind(':');
+        const std::size_t line = col == std::string::npos || col == 0 ? std::string::npos : str.rfind(':', col - 1);
+        const auto digits = [](std::string::const_iterator first, std::string::const_iterator last) {
+            return first != last && std::all_of(first, last, [](unsigned char c) { return std::isdigit(c); });
+        };
+        if (line != std::string::npos &&
+            digits(str.begin() + line + 1, str.begin() + col) &&
+            digits(str.begin() + col + 1, str.end()))
+            return "";
+    }
     if (nodeType == RecordDecl && str == "struct")
         return "";
     return str;
