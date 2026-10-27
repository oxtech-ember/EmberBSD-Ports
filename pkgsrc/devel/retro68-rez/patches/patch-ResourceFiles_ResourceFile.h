$NetBSD$

Select input formats and preserve native resource forks safely.

--- a/ResourceFiles/ResourceFile.h
+++ b/ResourceFiles/ResourceFile.h
@@ -29,6 +29,9 @@
     bool write(std::string path, Format f = Format::autodetect);
     bool read(std::istream& in, Format f);
     bool write(std::ostream& in, Format f);
+    // Read or replace only the native resource fork of an existing file.
+    bool readNativeResourceFork(const std::string& path);
+    bool writeNativeResourceFork(const std::string& path) const;
     static bool hasPlainDataFork(Format f);
     bool hasPlainDataFork();
     Format getFormat() { return format; }
