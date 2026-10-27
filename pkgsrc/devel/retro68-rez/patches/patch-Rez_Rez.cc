$NetBSD$

Select input formats and preserve native resource forks safely.

--- a/Rez/Rez.cc
+++ b/Rez/Rez.cc
@@ -44,6 +44,8 @@
         ("help,h", "show this help message")
         ("output,o", po::value<std::string>()->default_value("rez.output.rsrc"), "output file")
         ("append,a", "append to existing output file")
+        ("resource-fork-only", "append to an existing native resource fork without changing other file contents")
+        ("input-format", po::value<std::string>()->default_value("auto"), "input format: auto, text, or binary")
         ("type,t", po::value<std::string>()->default_value("rsrc"), "output file finder type code")
         ("creator,c", po::value<std::string>()->default_value("RSED"), "output file finder creator code")
         ("define,D", po::value<std::vector<std::string>>(), "predefine preprocessor symbol")
@@ -94,10 +96,32 @@
 
     std::string outfile = options["output"].as<std::string>();
     ResourceFile rsrcFile;
+    const std::string inputFormat = options["input-format"].as<std::string>();
+    const bool forkOnly = options.count("resource-fork-only");
+#ifndef __APPLE__
+    if (forkOnly) {
+        std::cerr << "ERROR: native resource forks are unsupported on this host\n";
+        return 1;
+    }
+#endif
+    if (inputFormat != "auto" && inputFormat != "text" && inputFormat != "binary") {
+        std::cerr << "ERROR: invalid input format: " << inputFormat << "\n";
+        return 1;
+    }
+    if (forkOnly && (!options.count("append") || options.count("data") || options.count("cc") ||
+                     !options["type"].defaulted() || !options["creator"].defaulted())) {
+        std::cerr << "ERROR: resource-fork-only requires append and excludes data, cc, type and creator\n";
+        return 1;
+    }
 
     if(options.count("append"))
     {
-        rsrcFile.read(outfile);
+        if (forkOnly && !rsrcFile.readNativeResourceFork(outfile)) {
+            std::cerr << "ERROR: cannot read native resource fork: " << outfile << "\n";
+            return 1;
+        }
+        if (!forkOnly)
+            rsrcFile.read(outfile);
 
         world.getResources().addResources(rsrcFile.resources);
     }
@@ -119,7 +143,8 @@
         for(std::string fn : options["input"].as<std::vector<std::string>>())
         {
             fs::path path(fn);
-            if(path.extension() == ".rsrc" || path.extension() == ".bin")
+            if(inputFormat == "binary" || (inputFormat == "auto" &&
+               (path.extension() == ".rsrc" || path.extension() == ".bin")))
             {
                 CopyBinaryResources(world, fn);
             }
@@ -154,7 +179,8 @@
                     }
 
                     RezParser parser(lexer, world);
-                    parser.parse();
+                    if (parser.parse() != 0)
+                        world.problem(Diagnostic(Diagnostic::error, "Resource parsing failed", yy::location(&fn)));
                 }
                 catch(...)
                 {
@@ -174,12 +200,18 @@
     {
         std::cerr << "Writing " << rsrcFile.resources.countResources() << " resources.\n";
     }
-    rsrcFile.write(outfile);
+    if (!(forkOnly ? rsrcFile.writeNativeResourceFork(outfile) : rsrcFile.write(outfile))) {
+        std::cerr << "ERROR: cannot write resource file: " << outfile << "\n";
+        return 1;
+    }
 
     if(options.count("cc"))
         for(std::string ccFile : options["cc"].as<std::vector<std::string>>())
         {
-            rsrcFile.write(ccFile);
+            if (!rsrcFile.write(ccFile)) {
+                std::cerr << "ERROR: cannot write resource file: " << ccFile << "\n";
+                return 1;
+            }
         }
 
     return 0;
