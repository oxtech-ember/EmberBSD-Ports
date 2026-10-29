$NetBSD$

Use shared shader toolchain libraries.

--- src/shadertools/qspirvcompiler.cpp.orig
+++ src/shadertools/qspirvcompiler.cpp
@@ -12,7 +12,7 @@
 QT_WARNING_DISABLE_GCC("-Wsuggest-override")
 #include <glslang/Public/ShaderLang.h>
 #include <glslang/Public/ResourceLimits.h>
-#include <SPIRV/GlslangToSpv.h>
+#include <glslang/SPIRV/GlslangToSpv.h>
 QT_WARNING_POP
 
 //#define TOKENIZER_DEBUG
@@ -49,7 +49,6 @@
     return true;
 }
 
-using namespace QtShaderTools;
 
 class Includer : public glslang::TShader::Includer
 {
@@ -147,7 +146,7 @@
         messages |= EShMsgDebugInfo;
 
     Includer includer;
-    if (!shader.parse(QtShaderTools::GetDefaultResources(), 100, false, EShMessages(messages), includer)) {
+    if (!shader.parse(GetDefaultResources(), 100, false, EShMessages(messages), includer)) {
         qWarning("QSpirvCompiler: Failed to parse shader");
         log = QString::fromUtf8(shader.getInfoLog()).trimmed();
         return false;
