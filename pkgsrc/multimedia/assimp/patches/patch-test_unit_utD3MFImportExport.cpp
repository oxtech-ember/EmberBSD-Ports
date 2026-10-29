$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Exercise 3MF export, archive entries, round-trip and output failure.
--- test/unit/utD3MFImportExport.cpp
+++ test/unit/utD3MFImportExport.cpp
@@ -45,6 +45,9 @@
 #include <assimp/scene.h>
 #include <assimp/Exporter.hpp>
 #include <assimp/Importer.hpp>
+#include <zip.h>
+#include <cstdio>
+#include <vector>
 
 #include "AssetLib/3MF/D3MFExporter.h"
 
@@ -84,16 +87,48 @@
 
 #ifndef ASSIMP_BUILD_NO_EXPORT
 
-TEST_F(utD3MFImporterExporter, export3MFtoMemTest) {
-    //EXPECT_TRUE(exporterTest());
-}
+TEST_F(utD3MFImporterExporter, export3MFFileRoundTrip) {
+    const char *output = "assimp-3mf-roundtrip.3mf";
+    std::remove(output);
+    Assimp::Importer input;
+    const aiScene *scene = input.ReadFile(ASSIMP_TEST_MODELS_DIR "/3MF/box.3mf", 0);
+    ASSERT_NE(nullptr, scene);
+    Assimp::Exporter exporter;
+    ASSERT_EQ(AI_SUCCESS, exporter.Export(scene, "3mf", output));
+
+    int error = 0;
+    zip_t *archive = zip_open(output, ZIP_RDONLY, &error);
+    ASSERT_NE(nullptr, archive);
+    const char *entries[] = {"[Content_Types].xml", "3D/3DModel.model", "_rels/.rels"};
+    for (const char *entry : entries) {
+        zip_stat_t stat;
+        zip_stat_init(&stat);
+        EXPECT_EQ(0, zip_stat(archive, entry, 0, &stat));
+        EXPECT_GT(stat.size, 0u);
+        EXPECT_EQ(ZIP_CM_DEFLATE, stat.comp_method);
+    }
+    EXPECT_EQ(0, zip_close(archive));
 
-TEST_F(utD3MFImporterExporter, roundtrip3MFtoMemTest) {
-    /*EXPECT_TRUE(exporterTest());
+    Assimp::Importer result;
+    const aiScene *roundtrip = result.ReadFile(output, 0);
+    ASSERT_NE(nullptr, roundtrip);
+    ASSERT_EQ(1u, roundtrip->mNumMeshes);
+    EXPECT_EQ(12u, roundtrip->mMeshes[0]->mNumFaces);
+    EXPECT_EQ(8u, roundtrip->mMeshes[0]->mNumVertices);
+    EXPECT_EQ(0, std::remove(output));
+}
 
-    Assimp::Importer importer;
-    const aiScene *scene = importer.ReadFile("test.3mf", 0);
-    EXPECT_NE(nullptr, scene));*/
+TEST_F(utD3MFImporterExporter, export3MFReportsUnwritablePath) {
+    const char *parent = "assimp-3mf-not-a-directory.tmp";
+    FILE *file = std::fopen(parent, "wb");
+    ASSERT_NE(nullptr, file);
+    ASSERT_EQ(0, std::fclose(file));
+    Assimp::Importer input;
+    const aiScene *scene = input.ReadFile(ASSIMP_TEST_MODELS_DIR "/3MF/box.3mf", 0);
+    ASSERT_NE(nullptr, scene);
+    Assimp::Exporter exporter;
+    EXPECT_NE(AI_SUCCESS, exporter.Export(scene, "3mf", "assimp-3mf-not-a-directory.tmp/output.3mf"));
+    EXPECT_EQ(0, std::remove(parent));
 }
 
 #endif // ASSIMP_BUILD_NO_EXPORT
