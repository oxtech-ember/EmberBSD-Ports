$NetBSD$

Include the standard declaration for shared_ptr and enable_shared_from_this.

--- tools/debugserver/source/JSONGenerator.h.orig
+++ tools/debugserver/source/JSONGenerator.h
@@ -10,6 +10,7 @@
 #define LLDB_TOOLS_DEBUGSERVER_SOURCE_JSONGENERATOR_H
 
 #include <iomanip>
+#include <memory>
 #include <sstream>
 #include <string>
 #include <utility>
