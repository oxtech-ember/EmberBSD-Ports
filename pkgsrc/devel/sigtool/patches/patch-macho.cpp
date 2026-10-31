$NetBSD$

Hold the load command start as std::streamoff. On NetBSD off_t is long
and std::streamoff is long long, so fpos - off_t is ambiguous.

--- macho.cpp.orig
+++ macho.cpp
@@ -130,7 +130,7 @@
     f.read(reinterpret_cast<char *>(&header), sizeof(header));
 
     for (int cmdIdx = 0; cmdIdx < header.nCommands; cmdIdx++) {
-        off_t start = f.tellg();
+        std::streamoff start = f.tellg();
 
         uint32_t type = ReadLE::readUInt32(f);
         uint32_t cmdSize = ReadLE::readUInt32(f);
