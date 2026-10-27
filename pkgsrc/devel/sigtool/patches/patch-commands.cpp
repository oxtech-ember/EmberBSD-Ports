$NetBSD$

Keep spawn arguments and temporary files owned on every error path.

--- commands.cpp.orig
+++ commands.cpp
@@ -252,23 +252,6 @@
     }
 
     return 0;
-}
-
-static char **toSpawnArgs(const std::vector<std::string> &args) {
-    char **spawnArgs = reinterpret_cast<char **>(
-            calloc(args.size() + 1, sizeof(char *)));
-    for (int i = 0; i < args.size(); i++) {
-        spawnArgs[i] = strdup(args[i].c_str());
-    }
-    spawnArgs[args.size()] = nullptr;
-    return spawnArgs;
-}
-
-static void freeArgs(char **spawnArgs, std::vector<std::string>::size_type size) {
-    for (int i = 0; i < size; i++) {
-        free(spawnArgs[i]);
-    }
-    free(spawnArgs);
 }
 
 // Compute the cdhash of every signed Mach-O slice in `filename` — the first
@@ -440,9 +423,21 @@
         arguments.push_back(std::to_string(len));
     }
 
-    std::unique_ptr<char, decltype(&std::free)> tempfileName{
-            strdup((binaryFile + "XXXXXX").c_str()), std::free};
-    int tempfile = mkstemp(tempfileName.get());
+    std::string name = binaryFile + "XXXXXX";
+    std::vector<char> tempfileName(name.begin(), name.end());
+    tempfileName.push_back('\0');
+    int tempfile = mkstemp(tempfileName.data());
+    if (tempfile < 0) {
+        throw std::runtime_error{std::string{"mkstemp failed: "} + strerror(errno)};
+    }
+    struct TempFileGuard {
+        int fd;
+        const char *name;
+        ~TempFileGuard() {
+            if (fd >= 0) close(fd);
+            if (name) unlink(name);
+        }
+    } tempGuard{tempfile, tempfileName.data()};
 
     struct stat sourceFileStat{};
     if (stat(binaryFile.c_str(), &sourceFileStat) != 0) {
@@ -453,17 +448,21 @@
     }
 
     arguments.emplace_back("-o");
-    arguments.emplace_back(std::string(tempfileName.get()));
+    arguments.emplace_back(std::string(tempfileName.data()));
 
     pid_t pid;
-    char **spawnArgs = toSpawnArgs(arguments);
+    std::vector<char *> spawnArgs;
+    spawnArgs.reserve(arguments.size() + 1);
+    for (const auto &arg : arguments)
+        spawnArgs.push_back(const_cast<char *>(arg.c_str()));
+    spawnArgs.push_back(nullptr);
     const char *codesign_allocate = getenv("CODESIGN_ALLOCATE");
     if (!codesign_allocate) {
         codesign_allocate = "codesign_allocate";
     }
 
     int spawn_result;
-    if ((spawn_result = posix_spawnp(&pid, codesign_allocate, nullptr, nullptr, spawnArgs, environ)) != 0) {
+    if ((spawn_result = posix_spawnp(&pid, codesign_allocate, nullptr, nullptr, spawnArgs.data(), environ)) != 0) {
         throw std::runtime_error{std::string{"Failed to spawn codesign_allocate: "} + strerror(spawn_result)};
     }
 
@@ -478,23 +477,23 @@
         };
     }
 
-    freeArgs(spawnArgs, arguments.size());
-
     if (!WIFEXITED(codesign_status) || WEXITSTATUS(codesign_status) != 0) {
         throw std::runtime_error{std::string{"codesign_failed: "} + std::to_string(WEXITSTATUS(codesign_status))};
     }
 
+    tempGuard.fd = -1;
     if (close(tempfile) != 0) {
-        throw std::runtime_error{std::string{"close: "} + strerror(tempfile)};
+        throw std::runtime_error{std::string{"close: "} + strerror(errno)};
     }
 
     Commands::SignOptions injectOpts = signTemplate;
-    injectOpts.filename = std::string(tempfileName.get());
+    injectOpts.filename = std::string(tempfileName.data());
     Commands::inject(injectOpts);
 
-    if (rename(tempfileName.get(), binaryFile.c_str()) != 0) {
+    if (rename(tempfileName.data(), binaryFile.c_str()) != 0) {
         throw std::runtime_error{"rename failed"};
     }
+    tempGuard.name = nullptr;
 }
 
 static void writeFileBytes(const std::string &path, const std::string &bytes) {
