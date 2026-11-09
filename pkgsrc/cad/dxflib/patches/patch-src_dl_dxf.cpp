$NetBSD$

Initialize auxiliary parser state and preserve KiCad FILE ownership and DXF fields.
The FILE API and entity fields originate in KiCad 10.0.8 thirdparty/dxflib_qcad
(GPL-2.0-or-later); retain upstream notices. EmberBSD adds scoped file/locale
cleanup and I/O error handling to the shared implementation.

--- src/dl_dxf.cpp.orig
+++ src/dl_dxf.cpp
@@ -29,6 +29,8 @@
 #include <cstdio>
 #include <cassert>
 #include <cmath>
+#include <locale>
+#include <memory>
 
 #include "dl_attributes.h"
 #include "dl_codes.h"
@@ -37,6 +39,15 @@
 
 #include "iostream"
 
+namespace {
+struct RestoreLocale {
+    std::locale previous;
+    RestoreLocale() : previous(std::locale::global(std::locale::classic())) {}
+    ~RestoreLocale() { std::locale::global(previous); }
+};
+}
+
+
 /**
  * Default constructor.
  */
@@ -65,6 +76,17 @@
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
 
 
@@ -108,20 +130,28 @@
  * @retval false If \p file could not be opened.
  */
 bool DL_Dxf::in(const std::string& file, DL_CreationInterface* creationInterface) {
-    FILE *fp;
+    return in(fopen(file.c_str(), "rt"), creationInterface);
+}
+
+/**
+ * Read an already-opened file, taking ownership even when reading or callbacks
+ * fail. A null file returns false. The path overload uses the same parser.
+ * As with the upstream path API, numeric parsing temporarily uses the C locale.
+ */
+bool DL_Dxf::in(FILE* fp, DL_CreationInterface* creationInterface) {
+    if (!fp) {
+        return false;
+    }
+    std::unique_ptr<FILE, int (*)(FILE*)> file(fp, fclose);
+    RestoreLocale restoreLocale;
+
     firstCall = true;
     currentObjectType = DL_UNKNOWN;
-
-    fp = fopen(file.c_str(), "rt");
-    if (fp) {
-        std::locale oldLocale = std::locale::global(std::locale("C"));	// use dot in numbers
-        while (readDxfGroups(fp, creationInterface)) {}
-        std::locale::global(oldLocale);
-        fclose(fp);
-        return true;
-    }
-
-    return false;
+    // readDxfGroups() only reports EOF. An I/O error need not set EOF.
+    while (!ferror(fp) && readDxfGroups(fp, creationInterface)) {}
+    const bool readOk = !ferror(fp);
+    const int closeResult = fclose(file.release());
+    return readOk && closeResult == 0;
 }
 
 
@@ -140,10 +170,11 @@
                 DL_CreationInterface* creationInterface) {
     
     if (stream.good()) {
+        RestoreLocale restoreLocale;
         firstCall=true;
         currentObjectType = DL_UNKNOWN;
-        while (readDxfGroups(stream, creationInterface)) {}
-        return true;
+        while (stream.good() && readDxfGroups(stream, creationInterface)) {}
+        return !stream.bad() && (stream.eof() || !stream.fail());
     }
     return false;
 }
@@ -239,6 +270,11 @@
         char* line;
 
         line = fgets(wholeLine, size, fp);
+        if (line == NULL) {
+            delete[] wholeLine;
+            s.clear();
+            return false;
+        }
 
         if (line!=NULL && line[0] != '\0') { // Evaluates to fgets() retval
             // line == wholeLine at this point.
@@ -270,16 +306,18 @@
 
     if (!stream.eof()) {
         // Only the useful part of the line
-        char* line = new char[size+1];
-        char* oriLine = line;
-        stream.getline(line, size);
+        std::unique_ptr<char[]> buffer(new char[size+1]);
+        char* line = buffer.get();
+        if (!stream.getline(line, size)) {
+            s.clear();
+            return false;
+        }
         stripWhiteSpace(&line, stripSpace);
         s = line;
         assert(size > s.length());
-        delete[] oriLine;
         return true;
     } else {
-        s[0] = '\0';
+        s.clear();
         return false;
     }
 }
@@ -963,7 +1001,8 @@
 void DL_Dxf::addPoint(DL_CreationInterface* creationInterface) {
     DL_PointData d(getRealValue(10, 0.0),
                    getRealValue(20, 0.0),
-                   getRealValue(30, 0.0));
+                   getRealValue(30, 0.0),
+                   getRealValue(39, 0.0));
     creationInterface->addPoint(d);
 }
 
@@ -1053,7 +1092,9 @@
     DL_VertexData d(getRealValue(10, 0.0),
                     getRealValue(20, 0.0),
                     getRealValue(30, 0.0),
-                    getRealValue(42, 0.0));
+                    getRealValue(42, 0.0),
+                    getRealValue(40, 0.0),
+                    getRealValue(41, 0.0));
 
     creationInterface->addVertex(d);
 }
