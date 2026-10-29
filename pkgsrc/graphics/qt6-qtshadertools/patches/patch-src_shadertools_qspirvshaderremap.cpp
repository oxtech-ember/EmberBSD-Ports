$NetBSD$

Use shared shader toolchain libraries.

--- src/shadertools/qspirvshaderremap.cpp.orig
+++ src/shadertools/qspirvshaderremap.cpp
@@ -2,48 +2,60 @@
 // SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
 // Qt-Security score:significant reason:default
 
-
 #include "qspirvshaderremap_p.h"
-
-#include <SPIRV/SPVRemapper.h>
+#include <spirv-tools/libspirv.hpp>
+#include <spirv-tools/optimizer.hpp>
+#include <cstring>
+#include <vector>
 
 QT_BEGIN_NAMESPACE
 
-void QSpirvShaderRemapper::remapErrorHandler(const std::string &s)
-{
-    if (!remapErrorMsg.isEmpty())
-        remapErrorMsg.append(QLatin1Char('\n'));
-    remapErrorMsg.append(QString::fromStdString(s));
-}
-
-void QSpirvShaderRemapper::remapLogHandler(const std::string &)
-{
-}
-
 QByteArray QSpirvShaderRemapper::remap(const QByteArray &ir, QSpirvShader::RemapFlags flags)
 {
+    remapErrorMsg.clear();
     if (ir.isEmpty())
-        return QByteArray();
-
-    remapErrorMsg.clear();
-
-    spv::spirvbin_t b;
-    b.registerErrorHandler(std::bind(&QSpirvShaderRemapper::remapErrorHandler, this, std::placeholders::_1));
-    b.registerLogHandler(std::bind(&QSpirvShaderRemapper::remapLogHandler, this, std::placeholders::_1));
-
-    const uint32_t opts = flags.testFlag(QSpirvShader::RemapFlag::StripOnly) ? spv::spirvbin_t::STRIP
-                                                                             : spv::spirvbin_t::DO_EVERYTHING;
-
-    std::vector<uint32_t> v;
-    v.resize(ir.size() / 4);
-    memcpy(v.data(), ir.constData(), v.size() * 4);
-
-    b.remap(v, opts);
-
-    if (!remapErrorMsg.isEmpty())
-        return QByteArray();
-
-    return QByteArray(reinterpret_cast<const char *>(v.data()), int(v.size()) * 4);
+        return {};
+    if (ir.size() % sizeof(uint32_t)) {
+        remapErrorMsg = QStringLiteral("SPIR-V byte length is not a multiple of four");
+        return {};
+    }
+    std::vector<uint32_t> input(ir.size() / sizeof(uint32_t));
+    std::memcpy(input.data(), ir.constData(), ir.size());
+    auto diagnostic = [this](spv_message_level_t level, const char *, const spv_position_t &,
+                             const char *message) {
+        if (level != SPV_MSG_FATAL && level != SPV_MSG_INTERNAL_ERROR && level != SPV_MSG_ERROR)
+            return;
+        if (!remapErrorMsg.isEmpty())
+            remapErrorMsg.append(QLatin1Char('\n'));
+        remapErrorMsg.append(QString::fromUtf8(message));
+    };
+    spvtools::SpirvTools validator(SPV_ENV_UNIVERSAL_1_6);
+    validator.SetMessageConsumer(diagnostic);
+    if (!validator.Validate(input)) {
+        if (remapErrorMsg.isEmpty())
+            remapErrorMsg = QStringLiteral("Invalid SPIR-V input");
+        return {};
+    }
+    spvtools::Optimizer optimizer(SPV_ENV_UNIVERSAL_1_6);
+    optimizer.SetMessageConsumer(diagnostic);
+    if (!flags.testFlag(QSpirvShader::RemapFlag::StripOnly)) {
+        optimizer.RegisterPass(spvtools::CreateLocalSingleStoreElimPass());
+        optimizer.RegisterPass(spvtools::CreateLocalSingleBlockLoadStoreElimPass());
+        optimizer.RegisterPass(spvtools::CreateEliminateDeadFunctionsPass());
+        optimizer.RegisterPass(spvtools::CreateAggressiveDCEPass(true, false));
+        optimizer.RegisterPass(spvtools::CreateCanonicalizeIdsPass());
+    }
+    optimizer.RegisterPass(spvtools::CreateStripDebugInfoPass());
+    spvtools::OptimizerOptions options;
+    options.set_preserve_bindings(true);
+    options.set_preserve_spec_constants(true);
+    std::vector<uint32_t> output;
+    if (!optimizer.Run(input.data(), input.size(), &output, options) || !validator.Validate(output)) {
+        if (remapErrorMsg.isEmpty())
+            remapErrorMsg = QStringLiteral("SPIR-V optimization failed");
+        return {};
+    }
+    return QByteArray(reinterpret_cast<const char *>(output.data()), qsizetype(output.size() * sizeof(uint32_t)));
 }
 
 QT_END_NAMESPACE
