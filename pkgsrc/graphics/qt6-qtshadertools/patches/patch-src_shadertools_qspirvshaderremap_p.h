$NetBSD$

Use shared shader toolchain libraries.

--- src/shadertools/qspirvshaderremap_p.h.orig
+++ src/shadertools/qspirvshaderremap_p.h
@@ -29,9 +29,6 @@
     QString errorMessage() const { return remapErrorMsg; }
 
 private:
-    void remapErrorHandler(const std::string &s);
-    void remapLogHandler(const std::string &s);
-
     QString remapErrorMsg;
 };
 
