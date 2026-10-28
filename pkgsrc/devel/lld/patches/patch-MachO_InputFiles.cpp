$NetBSD$

Preserve original addresses when rebasing Mach-O exception frame subtractors,
including sanitizer function prefixes and temporary local labels.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- MachO/InputFiles.cpp.orig
+++ MachO/InputFiles.cpp
@@ -504,6 +504,25 @@
   return d;
 }
 
+// Temporary local labels can have unwind entries without an input symbol.
+static Defined *findOrCreateUnwindSymbol(ObjFile *file,
+                                         ConcatInputSection *isec,
+                                         uint64_t off) {
+  if (Defined *d = tryFindSymbolAtOffset(isec, off))
+    return d;
+  if (isec->wasCoalesced)
+    return nullptr;
+  auto *d = make<Defined>(
+      saver().save(Twine("Lunwind.") + isec->getName() + "." +
+                   Twine::utohexstr(off)),
+      file, isec, off, /*size=*/0, /*isWeakDef=*/false,
+      /*isExternal=*/false, /*isPrivateExtern=*/false,
+      /*includeInSymtab=*/false, /*isReferencedDynamically=*/false,
+      /*noDeadStrip=*/false);
+  file->symbols.push_back(d);
+  return d;
+}
+
 template <class SectionHeader>
 static bool validateRelocationInfo(InputFile *file, const SectionHeader &sec,
                                    relocation_info rel) {
@@ -1218,30 +1237,10 @@
       // The functionAddress relocations are typically section relocations.
       // However, unwind info operates on a per-symbol basis, so we search for
       // the function symbol here.
-      Defined *d = tryFindSymbolAtOffset(referentIsec, add);
+      Defined *d = findOrCreateUnwindSymbol(this, referentIsec, add);
       if (!d) {
-        // If there's no symbol at the function address (e.g. for temporary
-        // local labels that are not in the symtab), synthesize a local one so
-        // we still emit correct unwind info.
-
-        // Avoid creating symbols for coalesced sections; those functions were
-        // folded away.
-        if (referentIsec->wasCoalesced) {
-          ++it;
-          continue;
-        }
-
-        d = make<Defined>(saver().save(Twine("Lcu.") + referentIsec->getName() +
-                                       "." + Twine::utohexstr(add)),
-                          this, referentIsec, add,
-                          /*size=*/0, /*isWeakDef=*/false,
-                          /*isExternal=*/false, /*isPrivateExtern=*/false,
-                          /*includeInSymtab=*/false,
-                          /*isReferencedDynamically=*/false,
-                          /*noDeadStrip=*/false);
-        // Also add to the file-level symbol list so that scanSymbols() in
-        // Writer picks it up and registers it with UnwindInfoSection.
-        symbols.push_back(d);
+        ++it;
+        continue;
       }
       d->originalUnwindEntry = isec;
       // Now that the symbol points to the unwind entry, we can remove the reloc
@@ -1380,41 +1379,64 @@
 //
 // If `Invert` is set, then we instead expect `target_addr - PC` to be written
 // to `PC`.
+static uint64_t getInputOffset(
+    const InputSection *isec,
+    DenseMap<const InputSection *, uint64_t> &inputOffsets) {
+  auto it = inputOffsets.find(isec);
+  if (it != inputOffsets.end())
+    return it->second;
+  for (const Subsection &subsec : isec->section.subsections)
+    inputOffsets.try_emplace(subsec.isec, subsec.offset);
+  return inputOffsets.find(isec)->second;
+}
+
 template <bool Invert = false>
 Defined *
 targetSymFromCanonicalSubtractor(const InputSection *isec,
-                                 std::vector<Relocation>::iterator relocIt) {
+                                 std::vector<Relocation>::iterator relocIt,
+                                 DenseMap<const InputSection *, uint64_t>
+                                     &inputOffsets) {
   Relocation &subtrahend = *relocIt;
   Relocation &minuend = *std::next(relocIt);
   assert(target->hasAttr(subtrahend.type, RelocAttrBits::SUBTRAHEND));
   assert(target->hasAttr(minuend.type, RelocAttrBits::UNSIGNED));
-  // Note: pcSym may *not* be exactly at the PC; there's usually a non-zero
-  // addend.
-  auto *pcSym = cast<Defined>(cast<macho::Symbol *>(subtrahend.referent));
-  Defined *target =
-      cast_or_null<Defined>(minuend.referent.dyn_cast<macho::Symbol *>());
-  if (!pcSym) {
-    auto *targetIsec =
-        cast<ConcatInputSection>(cast<InputSection *>(minuend.referent));
-    target = findSymbolAtOffset(targetIsec, minuend.addend);
-  }
-  if (Invert)
-    std::swap(pcSym, target);
-  if (pcSym->isec() == isec) {
-    if (pcSym->value - (Invert ? -1 : 1) * minuend.addend != subtrahend.offset)
-      fatal("invalid FDE relocation in __eh_frame");
+  Relocation &pcReloc = Invert ? minuend : subtrahend;
+  Relocation &targetReloc = Invert ? subtrahend : minuend;
+  auto *pcSym = cast<Defined>(cast<macho::Symbol *>(pcReloc.referent));
+  if (!pcSym->isec() || &pcSym->isec()->section != &isec->section)
+    fatal("invalid FDE relocation in __eh_frame");
+
+  InputSection *targetIsec;
+  uint64_t targetOffset = 0;
+  if (auto *sym = targetReloc.referent.dyn_cast<macho::Symbol *>()) {
+    auto *defined = cast<Defined>(sym);
+    targetIsec = defined->isec();
+    targetOffset = defined->value;
   } else {
-    // Ensure the pcReloc points to a symbol within the current EH frame.
-    // HACK: we should really verify that the original relocation's semantics
-    // are preserved. In particular, we should have
-    // `oldSym->value + oldOffset == newSym + newOffset`. However, we don't
-    // have an easy way to access the offsets from this point in the code; some
-    // refactoring is needed for that.
-    Relocation &pcReloc = Invert ? minuend : subtrahend;
-    pcReloc.referent = isec->symbols[0];
-    assert(isec->symbols[0]->value == 0);
-    minuend.addend = pcReloc.offset * (Invert ? 1LL : -1LL);
-  }
+    targetIsec = cast<InputSection *>(targetReloc.referent);
+  }
+  if (!targetIsec)
+    fatal("invalid FDE target in __eh_frame");
+
+  // Recover the target address before rebasing the PC to this split frame.
+  // The addend can also include an offset from a section symbol to the actual
+  // function, as it does for the function sanitizer's prefix data.
+  uint64_t addend = static_cast<uint64_t>(minuend.addend);
+  targetOffset += getInputOffset(targetIsec, inputOffsets) +
+                  getInputOffset(isec, inputOffsets) + subtrahend.offset -
+                  getInputOffset(pcSym->isec(), inputOffsets) - pcSym->value +
+                  (Invert ? -addend : addend);
+  auto *targetSubsec = cast<ConcatInputSection>(
+      findContainingSubsection(targetIsec->section, &targetOffset));
+  Defined *target = findOrCreateUnwindSymbol(
+      cast<ObjFile>(targetSubsec->getFile()), targetSubsec, targetOffset);
+  if (!target)
+    return nullptr;
+
+  targetReloc.referent = target;
+  pcReloc.referent = isec->symbols[0];
+  assert(isec->symbols[0]->value == 0);
+  minuend.addend = subtrahend.offset * (Invert ? 1LL : -1LL);
   return target;
 }
 
@@ -1441,6 +1463,7 @@
 // look for the "abs-ified" relocation if an explicit relocation is absent.
 void ObjFile::registerEhFrames(Section &ehFrameSection) {
   DenseMap<const InputSection *, CIE> cieMap;
+  DenseMap<const InputSection *, uint64_t> inputOffsets;
   for (const Subsection &subsec : ehFrameSection.subsections) {
     auto *isec = cast<ConcatInputSection>(subsec.isec);
     uint64_t isecOff = subsec.offset;
@@ -1471,9 +1494,11 @@
     InputSection *cieIsec = nullptr;
     if (cieOffRelocIt != isec->relocs.end()) {
       // We already have an explicit relocation for the CIE offset.
-      cieIsec =
-          targetSymFromCanonicalSubtractor</*Invert=*/true>(isec, cieOffRelocIt)
-              ->isec();
+      Defined *cieSym = targetSymFromCanonicalSubtractor</*Invert=*/true>(
+          isec, cieOffRelocIt, inputOffsets);
+      if (!cieSym)
+        fatal("failed to find CIE");
+      cieIsec = cieSym->isec();
       dataOff += sizeof(uint32_t);
     } else {
       // If we haven't found a relocation, then the CIE offset is most likely
@@ -1527,13 +1552,14 @@
 
     Defined *funcSym;
     if (funcAddrRelocIt != isec->relocs.end()) {
-      funcSym = targetSymFromCanonicalSubtractor(isec, funcAddrRelocIt);
+      funcSym =
+          targetSymFromCanonicalSubtractor(isec, funcAddrRelocIt, inputOffsets);
       // Canonicalize the symbol. If there are multiple symbols at the same
       // address, we want both `registerEhFrame` and `registerCompactUnwind`
       // to register the unwind entry under same symbol.
       // This is not particularly efficient, but we should run into this case
       // infrequently (only when handling the output of `ld -r`).
-      if (funcSym->isec())
+      if (funcSym && funcSym->isec())
         funcSym = findSymbolAtOffset(cast<ConcatInputSection>(funcSym->isec()),
                                      funcSym->value);
     } else {
@@ -1550,8 +1576,11 @@
 
     InputSection *lsdaIsec = nullptr;
     if (lsdaAddrRelocIt != isec->relocs.end()) {
-      lsdaIsec =
-          targetSymFromCanonicalSubtractor(isec, lsdaAddrRelocIt)->isec();
+      Defined *lsdaSym =
+          targetSymFromCanonicalSubtractor(isec, lsdaAddrRelocIt, inputOffsets);
+      if (!lsdaSym)
+        fatal("failed to find LSDA");
+      lsdaIsec = lsdaSym->isec();
     } else if (lsdaAddrOpt) {
       uint64_t lsdaAddr = *lsdaAddrOpt;
       Section *sec = findContainingSection(sections, &lsdaAddr);
