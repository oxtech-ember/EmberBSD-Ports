$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Use libzip for 3MF output, retaining entry data until archive close.
--- code/AssetLib/3MF/D3MFExporter.cpp
+++ code/AssetLib/3MF/D3MFExporter.cpp
@@ -53,11 +53,7 @@
 #include "3MFXmlTags.h"
 #include "D3MFOpcPackage.h"
 
-#ifdef ASSIMP_USE_HUNTER
-#include <zip/zip.h>
-#else
-#include <contrib/zip/src/zip.h>
-#endif
+#include <zip.h>
 
 namespace Assimp {
 
@@ -106,21 +102,35 @@
 }
 
 bool D3MFExporter::exportArchive(const char *file) {
-    bool ok(true);
-
-    mZipArchive = zip_open(file, ZIP_DEFAULT_COMPRESSION_LEVEL, 'w');
+    int error = 0;
+    mZipArchive = zip_open(file, ZIP_CREATE | ZIP_TRUNCATE, &error);
     if (nullptr == mZipArchive) {
         return false;
     }
 
-    ok |= exportContentTypes();
-    ok |= export3DModel();
-    ok |= exportRelations();
-
-    zip_close(mZipArchive);
+    try {
+        if (!exportContentTypes() || !export3DModel() || !exportRelations()) {
+            zip_discard(mZipArchive);
+            mZipArchive = nullptr;
+            mZipEntryData.clear();
+            return false;
+        }
+    } catch (...) {
+        zip_discard(mZipArchive);
+        mZipArchive = nullptr;
+        mZipEntryData.clear();
+        throw;
+    }
+
+    if (zip_close(mZipArchive) != 0) {
+        zip_discard(mZipArchive);
+        mZipArchive = nullptr;
+        mZipEntryData.clear();
+        return false;
+    }
     mZipArchive = nullptr;
-
-    return ok;
+    mZipEntryData.clear();
+    return true;
 }
 
 bool D3MFExporter::exportContentTypes() {
@@ -395,9 +405,21 @@
         throw DeadlyExportError("3MF-Export: Zip archive not valid, nullptr.");
     }
 
-    zip_entry_open(mZipArchive, entry.c_str());
-    zip_entry_write(mZipArchive, content.c_str(), content.size());
-    zip_entry_close(mZipArchive);
+    // libzip reads entries during zip_close, so each string must remain stable.
+    mZipEntryData.emplace_back(content);
+    const std::string &data = mZipEntryData.back();
+    zip_source_t *source = zip_source_buffer(mZipArchive, data.data(), data.size(), 0);
+    if (!source) {
+        throw DeadlyExportError("3MF-Export: cannot create ZIP source.");
+    }
+    const zip_int64_t index = zip_file_add(mZipArchive, entry.c_str(), source, ZIP_FL_ENC_UTF_8);
+    if (index < 0) {
+        zip_source_free(source);
+        throw DeadlyExportError("3MF-Export: cannot add ZIP entry.");
+    }
+    if (zip_set_file_compression(mZipArchive, static_cast<zip_uint64_t>(index), ZIP_CM_DEFLATE, 6) != 0) {
+        throw DeadlyExportError("3MF-Export: cannot set ZIP compression.");
+    }
 }
 
 } // Namespace D3MF
--- code/AssetLib/3MF/D3MFExporter.h
+++ code/AssetLib/3MF/D3MFExporter.h
@@ -43,6 +43,7 @@
 #ifndef ASSIMP_BUILD_NO_EXPORT
 #ifndef ASSIMP_BUILD_NO_3MF_EXPORTER
 
+#include <list>
 #include <sstream>
 #include <vector>
 #include <assimp/vector3.h>
@@ -52,7 +53,7 @@
 struct aiMaterial;
 struct aiMesh;
 
-struct zip_t;
+struct zip;
 
 namespace Assimp {
 
@@ -90,7 +91,8 @@
 
 private:
     std::string mArchiveName;
-    zip_t *mZipArchive{nullptr};
+    zip *mZipArchive{nullptr};
+    std::list<std::string> mZipEntryData;
     const aiScene *mScene{nullptr};
     std::ostringstream mModelOutput;
     std::ostringstream mRelOutput;
