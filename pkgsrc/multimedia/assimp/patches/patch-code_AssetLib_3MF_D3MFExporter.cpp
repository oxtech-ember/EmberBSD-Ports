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
-    m_zipArchive = zip_open(file, ZIP_DEFAULT_COMPRESSION_LEVEL, 'w');
+    int error = 0;
+    m_zipArchive = zip_open(file, ZIP_CREATE | ZIP_TRUNCATE, &error);
     if (nullptr == m_zipArchive) {
         return false;
     }
 
-    ok |= exportContentTypes();
-    ok |= export3DModel();
-    ok |= exportRelations();
+    try {
+        if (!exportContentTypes() || !export3DModel() || !exportRelations()) {
+            zip_discard(m_zipArchive);
+            m_zipArchive = nullptr;
+            mZipEntryData.clear();
+            return false;
+        }
+    } catch (...) {
+        zip_discard(m_zipArchive);
+        m_zipArchive = nullptr;
+        mZipEntryData.clear();
+        throw;
+    }
 
-    zip_close(m_zipArchive);
+    if (zip_close(m_zipArchive) != 0) {
+        zip_discard(m_zipArchive);
+        m_zipArchive = nullptr;
+        mZipEntryData.clear();
+        return false;
+    }
     m_zipArchive = nullptr;
-
-    return ok;
+    mZipEntryData.clear();
+    return true;
 }
 
 bool D3MFExporter::exportContentTypes() {
@@ -390,9 +400,21 @@
         throw DeadlyExportError("3MF-Export: Zip archive not valid, nullptr.");
     }
 
-    zip_entry_open(m_zipArchive, entry.c_str());
-    zip_entry_write(m_zipArchive, content.c_str(), content.size());
-    zip_entry_close(m_zipArchive);
+    // libzip reads entries during zip_close, so each string must remain stable.
+    mZipEntryData.emplace_back(content);
+    const std::string &data = mZipEntryData.back();
+    zip_source_t *source = zip_source_buffer(m_zipArchive, data.data(), data.size(), 0);
+    if (!source) {
+        throw DeadlyExportError("3MF-Export: cannot create ZIP source.");
+    }
+    const zip_int64_t index = zip_file_add(m_zipArchive, entry.c_str(), source, ZIP_FL_ENC_UTF_8);
+    if (index < 0) {
+        zip_source_free(source);
+        throw DeadlyExportError("3MF-Export: cannot add ZIP entry.");
+    }
+    if (zip_set_file_compression(m_zipArchive, static_cast<zip_uint64_t>(index), ZIP_CM_DEFLATE, 6) != 0) {
+        throw DeadlyExportError("3MF-Export: cannot set ZIP compression.");
+    }
 }
 
 } // Namespace D3MF
--- code/AssetLib/3MF/D3MFExporter.h
+++ code/AssetLib/3MF/D3MFExporter.h
@@ -44,6 +44,7 @@
 #ifndef ASSIMP_BUILD_NO_3MF_EXPORTER
 
 #include <memory>
+#include <list>
 #include <sstream>
 #include <vector>
 #include <assimp/vector3.h>
@@ -53,7 +54,7 @@
 struct aiMaterial;
 struct aiMesh;
 
-struct zip_t;
+struct zip;
 
 namespace Assimp {
 
@@ -92,7 +93,8 @@
 
 private:
     std::string mArchiveName;
-    zip_t *m_zipArchive;
+    zip *m_zipArchive;
+    std::list<std::string> mZipEntryData;
     const aiScene *mScene;
     std::ostringstream mModelOutput;
     std::ostringstream mRelOutput;
