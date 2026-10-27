$NetBSD$

Use the common CLI11 dependency.

--- codesign.cpp.orig
+++ codesign.cpp
@@ -1,5 +1,5 @@
 #include "commands.h"
-#include <CLI11.hpp>
+#include <CLI/CLI.hpp>
 #include <cstring>
 #include <iostream>
 
