$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- /dev/null
+++ src/gn/ffi/ports_adapters.h
@@ -0,0 +1,17 @@
+// Origin: EmberBSD (AI-assisted). Keep C++ views borrowed across CXX.
+#ifndef TOOLS_GN_FFI_PORTS_ADAPTERS_H_
+#define TOOLS_GN_FFI_PORTS_ADAPTERS_H_
+#include "rust/cxx.h"
+#include "gn/label.h"
+#include "gn/output_file.h"
+#include "gn/source_dir.h"
+#include "gn/value.h"
+#include <string_view>
+enum class ValueType : uint8_t;
+inline rust::Str PortsBorrow(std::string_view value) { return rust::Str(value.data(), value.size()); }
+inline rust::Str OutputFileValue(const OutputFile& value) { return PortsBorrow(value.value()); }
+inline rust::Str SourceDirValue(const SourceDir& value) { return PortsBorrow(value.SourceWithNoTrailingSlash()); }
+inline rust::Str LabelName(const Label& value) { return PortsBorrow(value.name()); }
+inline rust::Str ValueString(const Value& value) { return PortsBorrow(value.string_value()); }
+ValueType ValueKind(const Value& value);
+#endif
