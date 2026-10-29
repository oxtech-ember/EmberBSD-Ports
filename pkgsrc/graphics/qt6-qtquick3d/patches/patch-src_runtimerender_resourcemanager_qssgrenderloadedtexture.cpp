Use common external providers for Qt Quick 3D.

--- src/runtimerender/resourcemanager/qssgrenderloadedtexture.cpp.orig
+++ src/runtimerender/resourcemanager/qssgrenderloadedtexture.cpp
@@ -16,10 +16,6 @@
 
 #include <private/qtexturefilereader_p.h>
 
-#define TINYEXR_IMPLEMENTATION
-#define TINYEXR_USE_MINIZ 0
-#define TINYEXR_USE_THREAD 1
-#include <zlib.h>
 QT_WARNING_PUSH
 QT_WARNING_DISABLE_CLANG("-Wunused-parameter")
 QT_WARNING_DISABLE_CLANG("-Wunused-function")
@@ -560,15 +556,17 @@
 {
     QSSGLoadedTexture *imageData = nullptr;
 
-    char versionBuffer[tinyexr::kEXRVersionSize];
+    // OpenEXR version header: four-byte magic and four-byte version.
+    constexpr int exrVersionHeaderSize = 8;
+    char versionBuffer[exrVersionHeaderSize];
     source->seek(0);
-    auto size = source->read(versionBuffer, tinyexr::kEXRVersionSize);
+    auto size = source->read(versionBuffer, exrVersionHeaderSize);
     // Check if file is big enough
-    if (size != tinyexr::kEXRVersionSize)
+    if (size != exrVersionHeaderSize)
         return imageData;
     // Try to load the Version
     EXRVersion exrVersion;
-    if (ParseEXRVersionFromMemory(&exrVersion, reinterpret_cast<unsigned char *>(versionBuffer), tinyexr::kEXRVersionSize) != TINYEXR_SUCCESS)
+    if (ParseEXRVersionFromMemory(&exrVersion, reinterpret_cast<unsigned char *>(versionBuffer), exrVersionHeaderSize) != TINYEXR_SUCCESS)
         return imageData;
 
     // Check that the file is not a multipart file
