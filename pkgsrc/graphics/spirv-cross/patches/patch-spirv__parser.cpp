$NetBSD$

Recognize the subset of Shader.DebugInfo.102 emitted by glslang 16.6.

--- spirv_parser.cpp.orig
+++ spirv_parser.cpp
@@ -338,7 +338,10 @@
 			spirv_ext = SPIRExtension::SPV_AMD_gcn_shader;
 		else if (ext == "NonSemantic.DebugPrintf")
 			spirv_ext = SPIRExtension::NonSemanticDebugPrintf;
-		else if (ext == "NonSemantic.Shader.DebugInfo.100")
+		// glslang 16.6 emits .102 for the Source, Line and local-variable
+		// records handled below; unrecognized records remain ignored.
+		else if (ext == "NonSemantic.Shader.DebugInfo.100" ||
+		         ext == "NonSemantic.Shader.DebugInfo.102")
 			spirv_ext = SPIRExtension::NonSemanticShaderDebugInfo;
 		else if (ext.find("NonSemantic.") == 0)
 			spirv_ext = SPIRExtension::NonSemanticGeneric;
