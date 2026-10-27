$NetBSD$

Accept equal absolute symbols with value zero. Keep unknown bitcode
offsets separate from known ELF offsets.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- ELF/Symbols.cpp.orig
+++ ELF/Symbols.cpp
@@ -538,7 +538,8 @@
 }
 
 void elf::reportDuplicate(Ctx &ctx, const Symbol &sym, const InputFile *newFile,
-                          InputSectionBase *errSec, uint64_t errOffset) {
+                          InputSectionBase *errSec,
+                          std::optional<uint64_t> errOffset) {
   if (ctx.arg.allowMultipleDefinition)
     return;
   // In glibc<2.32, crti.o has .gnu.linkonce.t.__x86.get_pc_thunk.bx, which
@@ -547,8 +548,10 @@
   const Defined *d = dyn_cast<Defined>(&sym);
   if (!d || d->getName() == "__x86.get_pc_thunk.bx")
     return;
-  // Allow absolute symbols with the same value for GNU ld compatibility.
-  if (!d->section && !errSec && errOffset && d->value == errOffset)
+  // Allow absolute symbols with the same known value for GNU ld compatibility.
+  // Bitcode definitions do not have an ELF section or a known value yet.
+  if (!d->section && !errSec && errOffset &&
+      !isa_and_nonnull<BitcodeFile>(d->file) && d->value == *errOffset)
     return;
   if (!d->section || !errSec) {
     Err(ctx) << "duplicate symbol: " << &sym << "\n>>> defined in " << sym.file
@@ -563,6 +566,7 @@
   //   >>>            bar.o (/home/alice/src/bar.o)
   //   >>> defined at baz.c:563
   //   >>>            baz.o in archive libbaz.a
+  assert(errOffset && "section duplicate must have a known offset");
   auto *sec1 = cast<InputSectionBase>(d->section);
   auto diag = Err(ctx);
   diag << "duplicate symbol: " << &sym << "\n>>> defined at ";
@@ -572,10 +576,10 @@
     diag << "\n>>>            ";
   diag << sec1->getObjMsg(d->value) << "\n>>> defined at ";
   tell = diag.tell();
-  diag << errSec->getSrcMsg(sym, errOffset);
+  diag << errSec->getSrcMsg(sym, *errOffset);
   if (tell != diag.tell())
     diag << "\n>>>            ";
-  diag << errSec->getObjMsg(errOffset);
+  diag << errSec->getObjMsg(*errOffset);
 }
 
 void Symbol::checkDuplicate(Ctx &ctx, const Defined &other) const {
