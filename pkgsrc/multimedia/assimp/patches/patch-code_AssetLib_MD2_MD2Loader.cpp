$NetBSD$

Origin: upstream 7dbc85d9218fae017d4fad70269e7569f7b0c870
Authors: venkatchalla06, Claude Opus 4.8, Kim Kulling.
Prevent integer overflow when validating MD2 frame-table bounds.
--- code/AssetLib/MD2/MD2Loader.cpp
+++ code/AssetLib/MD2/MD2Loader.cpp
@@ -171,13 +171,17 @@ void MD2Importer::ValidateHeader( )
     }
 
     // -1 because Frame already contains one
-    unsigned int frameSize = sizeof (MD2::Frame) + (m_pcHeader->numVertices - 1) * sizeof(MD2::Vertex);
-
-    if (m_pcHeader->offsetSkins     + m_pcHeader->numSkins * sizeof (MD2::Skin)         >= fileSize ||
-        m_pcHeader->offsetTexCoords + m_pcHeader->numTexCoords * sizeof (MD2::TexCoord) >= fileSize ||
-        m_pcHeader->offsetTriangles + m_pcHeader->numTriangles * sizeof (MD2::Triangle) >= fileSize ||
-        m_pcHeader->offsetFrames    + m_pcHeader->numFrames * frameSize                 >= fileSize ||
-        m_pcHeader->offsetEnd           > fileSize)
+    // Compute in 64-bit: numVertices/numFrames are attacker-controlled uint32 header
+    // fields, so numFrames * frameSize (frameSize itself grows with numVertices) overflows
+    // a 32-bit product and can wrap past the file-size check below. The AI_MAX_ALLOC guards
+    // above only bound each count against sizeof(element), not against this product.
+    const uint64_t frameSize = (uint64_t)sizeof(MD2::Frame) + (uint64_t)(m_pcHeader->numVertices - 1) * sizeof(MD2::Vertex);
+
+    if ((uint64_t)m_pcHeader->offsetSkins     + (uint64_t)m_pcHeader->numSkins     * sizeof(MD2::Skin)     >= fileSize ||
+        (uint64_t)m_pcHeader->offsetTexCoords + (uint64_t)m_pcHeader->numTexCoords * sizeof(MD2::TexCoord) >= fileSize ||
+        (uint64_t)m_pcHeader->offsetTriangles + (uint64_t)m_pcHeader->numTriangles * sizeof(MD2::Triangle) >= fileSize ||
+        (uint64_t)m_pcHeader->offsetFrames    + (uint64_t)m_pcHeader->numFrames    * frameSize             >= fileSize ||
+        m_pcHeader->offsetEnd > fileSize)
     {
         throw DeadlyImportError("Invalid MD2 header: Some offsets are outside the file");
     }
