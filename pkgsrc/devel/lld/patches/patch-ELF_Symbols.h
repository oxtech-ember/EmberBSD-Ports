$NetBSD$

Accept equal absolute symbols with value zero. Keep unknown bitcode
offsets separate from known ELF offsets.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- ELF/Symbols.h.orig
+++ ELF/Symbols.h
@@ -19,6 +19,7 @@
 #include "llvm/ADT/DenseMap.h"
 #include "llvm/Object/ELF.h"
 #include "llvm/Support/Compiler.h"
+#include <optional>
 #include <tuple>
 
 namespace lld::elf {
@@ -530,7 +531,7 @@
 }
 
 void reportDuplicate(Ctx &, const Symbol &sym, const InputFile *newFile,
-                     InputSectionBase *errSec, uint64_t errOffset);
+                     InputSectionBase *errSec, std::optional<uint64_t> errOffset);
 void maybeWarnUnorderableSymbol(Ctx &, const Symbol *sym);
 bool computeIsPreemptible(Ctx &, const Symbol &sym);
 void parseVersionAndComputeIsPreemptible(Ctx &);
