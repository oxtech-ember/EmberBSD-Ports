$NetBSD$

Validate binary input and preserve native resource forks.

--- a/ResourceFiles/ResourceFile.cc
+++ b/ResourceFiles/ResourceFile.cc
@@ -7,9 +7,14 @@
 #include <ctime>
 #include <sstream>
 #include <iostream>
+#include <cerrno>
+#include <algorithm>
 
 #ifdef __APPLE__
+#include <fcntl.h>
 #include <sys/xattr.h>
+#include <sys/stat.h>
+#include <unistd.h>
 #endif
 extern "C" {
 #include "hfs.h"
@@ -17,6 +22,56 @@
 
 namespace fs = boost::filesystem;
 
+bool ResourceFile::readNativeResourceFork(const std::string& path)
+{
+#ifdef __APPLE__
+    struct stat st;
+    if (stat(path.c_str(), &st) != 0 || !S_ISREG(st.st_mode)) return false;
+    ssize_t size = getxattr(path.c_str(), XATTR_RESOURCEFORK_NAME, nullptr, 0, 0, 0);
+    if (size < 0 && errno != ENOATTR) return false;
+    if (size <= 0) {
+        resources.resources.clear();
+        return true;
+    }
+    std::string bytes(static_cast<size_t>(size), '\0');
+    if (getxattr(path.c_str(), XATTR_RESOURCEFORK_NAME, &bytes[0], bytes.size(), 0, 0) != size)
+        return false;
+    return resources.readChecked(bytes);
+#else
+    (void)path;
+    return false;
+#endif
+}
+
+bool ResourceFile::writeNativeResourceFork(const std::string& path) const
+{
+#ifdef __APPLE__
+    struct stat st;
+    if (stat(path.c_str(), &st) != 0 || !S_ISREG(st.st_mode)) return false;
+    std::ostringstream out(std::ios::out | std::ios::binary);
+    resources.writeFork(out);
+    if (!out) return false;
+    const std::string bytes = out.str();
+    const std::string forkPath = path + "/..namedfork/rsrc";
+    const int fd = open(forkPath.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0600);
+    if (fd < 0) return false;
+    size_t offset = 0;
+    bool ok = true;
+    while (offset < bytes.size()) {
+        const size_t amount = std::min(bytes.size() - offset, size_t(1024 * 1024));
+        ssize_t written = ::write(fd, bytes.data() + offset, amount);
+        if (written < 0 && errno == EINTR) continue;
+        if (written <= 0) { ok = false; break; }
+        offset += static_cast<size_t>(written);
+    }
+    if (close(fd) != 0) ok = false;
+    return ok;
+#else
+    (void)path;
+    return false;
+#endif
+}
+
 // CRC 16 table lookup array
 static unsigned short CRC16Table[256] =
     {0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
@@ -237,14 +292,20 @@
                     return false;
                 if(longword(in) != 0x00020000)
                     return false;
+                in.seekg(0, std::ios::end);
+                const std::streamoff fileSize = in.tellg();
+                if (fileSize < 26) return false;
                 in.seekg(24);
                 int n = word(in);
+                if (!in || n > (fileSize - 26) / 12) return false;
                 for(int i = 0; i < n; i++)
                 {
                     in.seekg(26 + i * 12);
                     int what = longword(in);
                     int off = longword(in);
                     int len = longword(in);
+                    if (!in || off < 0 || len < 0 || off > fileSize || len > fileSize - off)
+                        return false;
                     in.seekg(off);
                     switch(what)
                     {
@@ -256,18 +317,32 @@
                             }
                             break;
                         case 2:
-                            resources = Resources(in);
+                            {
+                                if (len == 0) {
+                                    resources.resources.clear();
+                                    break;
+                                }
+                                std::string fork(static_cast<size_t>(len), '\0');
+                                in.read(&fork[0], len);
+                                if (!in || !resources.readChecked(fork)) return false;
+                            }
                             break;
                         case 9:
+                            if (len < 8) return false;
                             type = ostype(in);
                             creator = ostype(in);
                             break;
                     }
+                    if (!in) return false;
                 }
             }
             break;
         case Format::macbin:
             {
+                in.seekg(0, std::ios::end);
+                const std::streamoff fileSize = in.tellg();
+                if (fileSize < 128) return false;
+                in.seekg(0);
                 if(byte(in) != 0)
                     return false;
                 if(byte(in) > 63)
@@ -277,7 +352,12 @@
                 creator = ostype(in);
                 in.seekg(83);
                 int datasize = longword(in);
-                //int rsrcsize = longword(in);
+                int rsrcsize = longword(in);
+                if (!in || datasize < 0 || rsrcsize < 0 || datasize > fileSize - 128)
+                    return false;
+                const std::streamoff paddedData = (std::streamoff(datasize) + 127) & ~std::streamoff(127);
+                if (paddedData > fileSize - 128 || rsrcsize > fileSize - 128 - paddedData)
+                    return false;
 
                 in.seekg(0);
                 char header[124];
@@ -289,9 +369,14 @@
                 std::vector<char> buf(datasize);
                 in.read(buf.data(), datasize);
                 data = std::string(buf.begin(), buf.end());
-                datasize = ((int)datasize + 0x7F) & ~0x7F;
-                in.seekg(128 + datasize);
-                resources = Resources(in);
+                in.seekg(128 + paddedData);
+                if (rsrcsize) {
+                    std::string fork(static_cast<size_t>(rsrcsize), '\0');
+                    in.read(&fork[0], rsrcsize);
+                    if (!in || !resources.readChecked(fork)) return false;
+                } else {
+                    resources.resources.clear();
+                }
             }
             break;
         default:
