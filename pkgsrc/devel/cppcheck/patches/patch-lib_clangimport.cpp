# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
# Keep pseudo-file coordinates intact without reinterpreting physical paths.

--- lib/clangimport.cpp.orig
+++ lib/clangimport.cpp
@@ -134,8 +134,31 @@
             pos1 = line.find_first_not_of(' ', pos1 + 1);
             continue;
         }
-        if (line[pos1] == '<')
-            pos2 = line.find('>', pos1);
+        if (line[pos1] == '<') {
+            // Only a coordinate's leading <name>: denotes a pseudo-file.
+            // Physical filenames may themselves contain an unmatched '<'.
+            bool filenameStart = true;
+            for (pos2 = pos1 + 1; pos2 < line.size(); ++pos2) {
+                if (line[pos2] == '<' && filenameStart) {
+                    const auto end = line.find('>', pos2 + 1);
+                    if (end != std::string::npos &&
+                        ((end + 1 < line.size() && line[end + 1] == ':') ||
+                         line.compare(pos2, end - pos2 + 1, "<invalid sloc>") == 0)) {
+                        pos2 = end;
+                        filenameStart = false;
+                        continue;
+                    }
+                }
+                if (line[pos2] == '>')
+                    break;
+                if (line[pos2] == ',')
+                    filenameStart = true;
+                else if (line[pos2] != ' ')
+                    filenameStart = false;
+            }
+            if (pos2 == line.size())
+                throw InternalError(nullptr, "unterminated AST location: " + line.substr(pos1), InternalError::AST);
+        }
         else if (line[pos1] == '\"')
             pos2 = line.find('\"', pos1+1);
         else if (line[pos1] == '\'') {
@@ -573,7 +596,7 @@
             else {
                 // "<invalid sloc>" are encountered in every AST dump by some built-in TypedefDecl
                 // an completely empty location block was encountered with a CompoundStmt
-                if (ext != "<<invalid sloc>" && ext != "<>")
+                if (ext != "<<invalid sloc>>" && ext != "<>")
                     throw InternalError(nullptr, "invalid AST location: " + ext, InternalError::AST);
             }
         }
