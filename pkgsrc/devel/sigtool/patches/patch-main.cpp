$NetBSD$

Use the common CLI11 dependency.

--- main.cpp.orig
+++ main.cpp
@@ -1,5 +1,5 @@
 #include "commands.h"
-#include <CLI11.hpp>
+#include <CLI/CLI.hpp>
 #include <iostream>
 
 static int run(int argc, char **argv);
