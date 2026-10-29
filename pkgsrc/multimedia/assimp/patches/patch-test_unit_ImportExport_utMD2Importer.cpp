$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Reject MD2 frame table lengths that wrap in 32-bit arithmetic.
--- test/unit/ImportExport/utMD2Importer.cpp
+++ test/unit/ImportExport/utMD2Importer.cpp
@@ -76,3 +76,21 @@
     const aiScene *scene = importer.ReadFile(ASSIMP_TEST_MODELS_NONBSD_DIR "/MD2/horse.md2", aiProcess_ValidateDataStructure);
     ASSERT_NE(nullptr, scene);
 }
+
+TEST(utMD2Importer, RejectWrappedFrameTable) {
+    unsigned char data[512] = {};
+    auto put32 = [&data](size_t word, uint32_t value) {
+        for (size_t i = 0; i < 4; ++i)
+            data[word * 4 + i] = static_cast<unsigned char>(value >> (8 * i));
+    };
+    put32(0, 0x32504449); // IDP2, little endian
+    put32(1, 8);
+    put32(6, 1014);      // 4096-byte frame
+    put32(10, 1048576);  // 32-bit frame table size wraps to zero
+    for (size_t word = 11; word <= 15; ++word)
+        put32(word, 68);
+    put32(16, sizeof(data));
+    Assimp::Importer importer;
+    EXPECT_EQ(nullptr, importer.ReadFileFromMemory(data, sizeof(data), 0, "md2"));
+    EXPECT_NE(nullptr, std::strstr(importer.GetErrorString(), "Some offsets are outside the file"));
+}
