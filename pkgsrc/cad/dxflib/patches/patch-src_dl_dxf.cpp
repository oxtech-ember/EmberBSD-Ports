$NetBSD$

Initialize auxiliary parser state to avoid uninitialized reads.
--- src/dl_dxf.cpp.orig
+++ src/dl_dxf.cpp
@@ -65,6 +65,17 @@
     leaderVertices = NULL;
     maxLeaderVertices = 0;
     leaderVertexIndex = 0;
+
+    // Initialize parser state before the first read.
+    firstHatchLoop = true;
+    xRecordValues = false;
+    groupCode = 0;
+    currentObjectType = 0;
+    settingValue[0] = 0;
+    firstCall = true;
+    libVersion = 0;
+    appDictionaryHandle = 0;
+    styleHandleStd = 0;
 }
 
 
