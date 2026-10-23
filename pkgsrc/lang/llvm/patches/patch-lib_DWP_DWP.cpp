$NetBSD$

Origin: EmberBSD (AI-assisted), LLVM 23.1.2 DWP offset widths and bounds.
Preserve per-unit string-offset widths and DWARF4 type headers. Reject truncated
contributions and invalid string references without non-advancing reads.
Not submitted upstream. SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

--- lib/DWP/DWP.cpp.orig
+++ lib/DWP/DWP.cpp
@@ -29,16 +29,40 @@
 using namespace llvm;
 using namespace llvm::object;
 
-// Returns the size of debug_str_offsets section headers in bytes.
-static uint64_t debugStrOffsetsHeaderSize(DataExtractor StrOffsetsData,
-                                          uint16_t DwarfVersion) {
-  if (DwarfVersion <= 4)
-    return 0; // There is no header before dwarf 5.
-  uint64_t Offset = 0;
-  uint64_t Length = StrOffsetsData.getU32(&Offset);
-  if (Length == llvm::dwarf::DW_LENGTH_DWARF64)
-    return 16; // unit length: 12 bytes, version: 2 bytes, padding: 2 bytes.
-  return 8;    // unit length: 4 bytes, version: 2 bytes, padding: 2 bytes.
+using StringOffsetsRemapping =
+    DenseMap<std::pair<uint64_t, uint64_t>, std::pair<uint64_t, uint64_t>>;
+
+struct StringOffsetsHeader {
+  uint64_t HeaderSize;
+  uint64_t OffsetSize;
+  uint64_t End;
+};
+
+static Expected<StringOffsetsHeader>
+parseStringOffsetsHeader(DataExtractor Data, uint64_t Offset, uint16_t Version,
+                         dwarf::DwarfFormat Format, uint64_t End) {
+  const uint64_t Start = Offset;
+  if (End > Data.size() || Offset > End)
+    return make_error<DWPError>("string offsets contribution exceeds section");
+  uint64_t OffsetSize = dwarf::getDwarfOffsetByteSize(Format);
+  if (Version >= 5) {
+    DWARFDataExtractor HeaderData(Data.getData().substr(0, End), true, 0);
+    Error Err = Error::success();
+    uint64_t Length;
+    std::tie(Length, Format) = HeaderData.getInitialLength(&Offset, &Err);
+    if (Err)
+      return make_error<DWPError>("invalid string offsets header: " +
+                                  toString(std::move(Err)));
+    if (Length < 4 || Length > End - Offset)
+      return make_error<DWPError>("invalid string offsets contribution length");
+    End = Offset + Length;
+    if (HeaderData.getU16(&Offset) != 5 || HeaderData.getU16(&Offset) != 0)
+      return make_error<DWPError>("invalid string offsets version or padding");
+    OffsetSize = dwarf::getDwarfOffsetByteSize(Format);
+  }
+  if ((End - Offset) % OffsetSize != 0)
+    return make_error<DWPError>("truncated string offset entry");
+  return StringOffsetsHeader{Offset - Start, OffsetSize, End};
 }
 
 static Expected<uint64_t> getCUAbbrev(StringRef Abbrev, uint64_t AbbrCode) {
@@ -68,26 +92,32 @@
 
 static Expected<const char *>
 getIndexedString(dwarf::Form Form, DataExtractor InfoData, uint64_t &InfoOffset,
-                 StringRef StrOffsets, StringRef Str, uint16_t Version) {
-  if (Form == dwarf::DW_FORM_string)
-    return InfoData.getCStr(&InfoOffset);
+                 StringRef StrOffsets, StringRef Str, uint16_t Version,
+                 dwarf::DwarfFormat Format) {
+  if (Form == dwarf::DW_FORM_string) {
+    const char *String = InfoData.getCStr(&InfoOffset);
+    if (!String)
+      return make_error<DWPError>("unterminated inline string");
+    return String;
+  }
   uint64_t StrIndex;
+  Error Err = Error::success();
   switch (Form) {
   case dwarf::DW_FORM_strx1:
-    StrIndex = InfoData.getU8(&InfoOffset);
+    StrIndex = InfoData.getU8(&InfoOffset, &Err);
     break;
   case dwarf::DW_FORM_strx2:
-    StrIndex = InfoData.getU16(&InfoOffset);
+    StrIndex = InfoData.getU16(&InfoOffset, &Err);
     break;
   case dwarf::DW_FORM_strx3:
-    StrIndex = InfoData.getU24(&InfoOffset);
+    StrIndex = InfoData.getU24(&InfoOffset, &Err);
     break;
   case dwarf::DW_FORM_strx4:
-    StrIndex = InfoData.getU32(&InfoOffset);
+    StrIndex = InfoData.getU32(&InfoOffset, &Err);
     break;
   case dwarf::DW_FORM_strx:
   case dwarf::DW_FORM_GNU_str_index:
-    StrIndex = InfoData.getULEB128(&InfoOffset);
+    StrIndex = InfoData.getULEB128(&InfoOffset, &Err);
     break;
   default:
     return make_error<DWPError>(
@@ -95,13 +125,23 @@
         "DW_FORM_string, DW_FORM_strx, DW_FORM_strx1, DW_FORM_strx2, "
         "DW_FORM_strx3, DW_FORM_strx4, or DW_FORM_GNU_str_index.");
   }
+  if (Err)
+    return make_error<DWPError>("invalid string index: " + toString(std::move(Err)));
   DataExtractor StrOffsetsData(StrOffsets, true);
-  uint64_t StrOffsetsOffset = 4 * StrIndex;
-  StrOffsetsOffset += debugStrOffsetsHeaderSize(StrOffsetsData, Version);
-
-  uint64_t StrOffset = StrOffsetsData.getU32(&StrOffsetsOffset);
+  auto Header = parseStringOffsetsHeader(StrOffsetsData, 0, Version, Format,
+                                         StrOffsets.size());
+  if (!Header)
+    return Header.takeError();
+  if (StrIndex >= (Header->End - Header->HeaderSize) / Header->OffsetSize)
+    return make_error<DWPError>("string index exceeds offsets contribution");
+  uint64_t StrOffsetsOffset = Header->HeaderSize + Header->OffsetSize * StrIndex;
+  uint64_t StrOffset =
+      StrOffsetsData.getUnsigned(&StrOffsetsOffset, Header->OffsetSize);
   DataExtractor StrData(Str, true);
-  return StrData.getCStr(&StrOffset);
+  const char *String = StrData.getCStr(&StrOffset);
+  if (!String)
+    return make_error<DWPError>("invalid string offset or unterminated string");
+  return String;
 }
 
 static Expected<CompileUnitIdentifiers>
@@ -136,7 +176,7 @@
     switch (Name) {
     case dwarf::DW_AT_name: {
       Expected<const char *> EName = getIndexedString(
-          Form, InfoData, Offset, StrOffsets, Str, Header.Version);
+          Form, InfoData, Offset, StrOffsets, Str, Header.Version, Header.Format);
       if (!EName)
         return EName.takeError();
       ID.Name = *EName;
@@ -145,7 +185,7 @@
     case dwarf::DW_AT_GNU_dwo_name:
     case dwarf::DW_AT_dwo_name: {
       Expected<const char *> EName = getIndexedString(
-          Form, InfoData, Offset, StrOffsets, Str, Header.Version);
+          Form, InfoData, Offset, StrOffsets, Str, Header.Version, Header.Format);
       if (!EName)
         return EName.takeError();
       ID.DWOName = *EName;
@@ -221,7 +261,7 @@
     const DWARFUnitIndex &TUIndex, DWPSectionId OutputSection, StringRef Types,
     const UnitIndexEntry &TUEntry, uint32_t &TypesOffset,
     unsigned TypesContributionIndex, OnCuIndexOverflow OverflowOptValue,
-    bool &AnySectionOverflow) {
+    bool &AnySectionOverflow, const StringOffsetsRemapping &StrRemapping) {
   Out.switchSection(OutputSection);
   for (const DWARFUnitIndex::Entry &E : TUIndex.getRows()) {
     auto *I = E.getContributions();
@@ -238,8 +278,15 @@
         continue;
       auto &C =
           Entry.Contributions[getContributionIndex(Kind, TUIndex.getVersion())];
-      C.setOffset(C.getOffset() + I->getOffset());
-      C.setLength(I->getLength());
+      auto Mapped = StrRemapping.find({I->getOffset(), I->getLength()});
+      if (Kind == DW_SECT_STR_OFFSETS && TUIndex.getVersion() >= 5 &&
+          Mapped != StrRemapping.end()) {
+        C.setOffset(C.getOffset() + Mapped->second.first);
+        C.setLength(Mapped->second.second);
+      } else {
+        C.setOffset(C.getOffset() + I->getOffset());
+        C.setLength(I->getLength());
+      }
       ++I;
     }
     auto &C = Entry.Contributions[TypesContributionIndex];
@@ -273,7 +320,7 @@
   for (StringRef Types : TypesSections) {
     Out.switchSection(OutputSection);
     uint64_t Offset = 0;
-    DataExtractor Data(Types, true);
+    DWARFDataExtractor Data(Types, true, 0);
     while (Data.isValidOffset(Offset)) {
       UnitIndexEntry Entry = CUEntry;
       // Zero out the debug_info contribution
@@ -281,14 +328,21 @@
       auto &C = Entry.Contributions[getContributionIndex(DW_SECT_EXT_TYPES, 2)];
       C.setOffset(TypesOffset);
       auto PrevOffset = Offset;
-      // Length of the unit, including the 4 byte length field.
-      C.setLength(Data.getU32(&Offset) + 4);
-
-      Data.getU16(&Offset); // Version
-      Data.getU32(&Offset); // Abbrev offset
-      Data.getU8(&Offset);  // Address size
+      Error Err = Error::success();
+      auto [Length, Format] = Data.getInitialLength(&Offset, &Err);
+      if (Err)
+        return make_error<DWPError>("invalid type unit length: " +
+                                    toString(std::move(Err)));
+      const uint64_t OffsetSize = dwarf::getDwarfOffsetByteSize(Format);
+      if (Length > Types.size() - Offset || Length < 11 + 2 * OffsetSize)
+        return make_error<DWPError>("invalid type unit contribution length");
+      C.setLength(Length + dwarf::getUnitLengthFieldByteSize(Format));
+      if (Data.getU16(&Offset) != 4)
+        return make_error<DWPError>("unsupported .debug_types unit version");
+      Data.getUnsigned(&Offset, OffsetSize); // Abbreviation offset.
+      Data.getU8(&Offset);                   // Address size.
       auto Signature = Data.getU64(&Offset);
-      Offset = PrevOffset + C.getLength32();
+      Offset = PrevOffset + C.getLength();
 
       auto P = TypeIndexEntries.insert(std::make_pair(Signature, Entry));
       if (!P.second)
@@ -380,18 +434,22 @@
 
 // Create a mask so we don't trigger a emitIntValue() assert below if the
 // NewOffset is over 4GB.
-static void writeNewOffsetsTo(DWPWriter &Out, DataExtractor &Data,
+static Error writeNewOffsetsTo(DWPWriter &Out, DataExtractor &Data,
                               DenseMap<uint64_t, uint64_t> &OffsetRemapping,
                               uint64_t &Offset, const uint64_t Size,
                               uint32_t OldOffsetSize, uint32_t NewOffsetSize) {
   const uint64_t NewOffsetMask = NewOffsetSize == 8 ? UINT64_MAX : UINT32_MAX;
   while (Offset < Size) {
     const uint64_t OldOffset = Data.getUnsigned(&Offset, OldOffsetSize);
-    const uint64_t NewOffset = OffsetRemapping[OldOffset];
+    auto It = OffsetRemapping.find(OldOffset);
+    if (It == OffsetRemapping.end())
+      return make_error<DWPError>("invalid string offset in contribution");
+    const uint64_t NewOffset = It->second;
     // Truncate the string offset like the old llvm-dwp would have if we aren't
     // promoting the .debug_str_offsets to DWARF64.
     Out.emitIntValue(NewOffset & NewOffsetMask, NewOffsetSize);
   }
+  return Error::success();
 }
 
 namespace llvm {
@@ -407,7 +465,7 @@
     return make_error<DWPError>("cannot parse compile unit length: " +
                                 llvm::toString(std::move(Err)));
 
-  if (!InfoData.isValidOffset(Offset + (Header.Length - 1))) {
+  if (Header.Length > InfoData.size() - Offset) {
     return make_error<DWPError>(
         "compile unit exceeds .debug_info section range: " +
         utostr(Offset + Header.Length) + " >= " + utostr(InfoData.size()));
@@ -418,14 +476,15 @@
     return make_error<DWPError>("cannot parse compile unit version: " +
                                 llvm::toString(std::move(Err)));
 
+  uint64_t OffsetSize = dwarf::getDwarfOffsetByteSize(Header.Format);
   uint64_t MinHeaderLength;
   if (Header.Version >= 5) {
-    // Size: Version (2), UnitType (1), AddrSize (1), DebugAbbrevOffset (4),
+    // Size: Version (2), UnitType (1), AddrSize (1), DebugAbbrevOffset (OffsetSize),
     // Signature (8)
-    MinHeaderLength = 16;
+    MinHeaderLength = 12 + OffsetSize;
   } else {
-    // Size: Version (2), DebugAbbrevOffset (4), AddrSize (1)
-    MinHeaderLength = 7;
+    // Size: Version (2), DebugAbbrevOffset (OffsetSize), AddrSize (1)
+    MinHeaderLength = 3 + OffsetSize;
   }
   if (Header.Length < MinHeaderLength) {
     return make_error<DWPError>("unit length is too small: expected at least " +
@@ -435,19 +494,19 @@
   if (Header.Version >= 5) {
     Header.UnitType = InfoData.getU8(&Offset);
     Header.AddrSize = InfoData.getU8(&Offset);
-    Header.DebugAbbrevOffset = InfoData.getU32(&Offset);
+    Header.DebugAbbrevOffset = InfoData.getUnsigned(&Offset, OffsetSize);
     Header.Signature = InfoData.getU64(&Offset);
     if (Header.UnitType == dwarf::DW_UT_split_type) {
       // Type offset.
-      MinHeaderLength += 4;
+      MinHeaderLength += OffsetSize;
       if (Header.Length < MinHeaderLength)
         return make_error<DWPError>("type unit is missing type offset");
-      InfoData.getU32(&Offset);
+      InfoData.getUnsigned(&Offset, OffsetSize);
     }
   } else {
     // Note that, address_size and debug_abbrev_offset fields have switched
     // places between dwarf version 4 and 5.
-    Header.DebugAbbrevOffset = InfoData.getU32(&Offset);
+    Header.DebugAbbrevOffset = InfoData.getUnsigned(&Offset, OffsetSize);
     Header.AddrSize = InfoData.getU8(&Offset);
   }
 
@@ -455,119 +514,135 @@
   return Header;
 }
 
-static void
+struct StringOffsetsContribution {
+  uint64_t Offset;
+  uint64_t Length;
+  dwarf::DwarfFormat Format;
+};
+
+static Error
 writeStringsAndOffsets(DWPWriter &Out, DWPStringPool &Strings,
                        StringRef CurStrSection, StringRef CurStrOffsetSection,
                        uint16_t Version, SectionLengths &SectionLength,
+                       ArrayRef<StringOffsetsContribution> Contributions,
                        const Dwarf64StrOffsetsPromotion StrOffsetsOptValue,
-                       bool SingleInput) {
-  // Could possibly produce an error or warning if one of these was non-null but
-  // the other was null.
-  if (CurStrSection.empty() || CurStrOffsetSection.empty())
-    return;
-
-  // Fast path: when there is only one input, all strings are unique and offsets
-  // don't need remapping. Copy both sections directly without any hashing.
-  if (SingleInput && StrOffsetsOptValue != Dwarf64StrOffsetsPromotion::Always) {
-    Out.switchSection(DS_Str);
-    Out.emitBytes(CurStrSection);
-    Out.switchSection(DS_StrOffsets);
-    Out.emitBytes(CurStrOffsetSection);
-    return;
-  }
+                       bool SingleInput, StringOffsetsRemapping &Remapping) {
+  if (CurStrOffsetSection.empty())
+    return Error::success();
 
+  const bool CopyOnly = SingleInput &&
+      StrOffsetsOptValue != Dwarf64StrOffsetsPromotion::Always;
   DenseMap<uint64_t, uint64_t> OffsetRemapping;
-  // Pre-reserve based on estimated string count to avoid rehashing.
-  OffsetRemapping.reserve(CurStrSection.size() / 20);
-
+  if (!CopyOnly)
+    OffsetRemapping.reserve(CurStrSection.size() / 20);
   DataExtractor Data(CurStrSection, true);
   uint64_t LocalOffset = 0;
   uint64_t PrevOffset = 0;
-
-  // Keep track if any new string offsets exceed UINT32_MAX. If any do, we can
-  // emit a DWARF64 .debug_str_offsets table for this compile unit. If the
-  // \a StrOffsetsOptValue argument is Dwarf64StrOffsetsPromotion::Always, then
-  // force the emission of DWARF64 .debug_str_offsets for testing.
-  uint32_t OldOffsetSize = 4;
-  uint32_t NewOffsetSize =
-      StrOffsetsOptValue == Dwarf64StrOffsetsPromotion::Always ? 8 : 4;
+  bool Needs64 = false;
   Out.switchSection(DS_Str);
-  while (const char *S = Data.getCStr(&LocalOffset)) {
-    uint64_t NewOffset = Strings.getOffset(S, LocalOffset - PrevOffset);
-    OffsetRemapping[PrevOffset] = NewOffset;
-    // Only promote the .debug_str_offsets to DWARF64 if our setting allows it.
-    if (StrOffsetsOptValue != Dwarf64StrOffsetsPromotion::Disabled &&
-        NewOffset > UINT32_MAX) {
-      NewOffsetSize = 8;
+  while (LocalOffset < Data.size()) {
+    const char *S = Data.getCStr(&LocalOffset);
+    if (!S)
+      return make_error<DWPError>("unterminated string section");
+    if (!CopyOnly) {
+      uint64_t NewOffset = Strings.getOffset(S, LocalOffset - PrevOffset);
+      OffsetRemapping[PrevOffset] = NewOffset;
+      Needs64 |= NewOffset > UINT32_MAX;
     }
     PrevOffset = LocalOffset;
   }
 
   Data = DataExtractor(CurStrOffsetSection, true);
-
-  Out.switchSection(DS_StrOffsets);
-
-  uint64_t Offset = 0;
-  uint64_t Size = CurStrOffsetSection.size();
-  if (Version > 4) {
-    while (Offset < Size) {
-      const uint64_t HeaderSize = debugStrOffsetsHeaderSize(Data, Version);
-      assert(HeaderSize <= Size - Offset &&
-             "StrOffsetSection size is less than its header");
-
-      uint64_t ContributionEnd = 0;
-      uint64_t ContributionSize = 0;
-      uint64_t HeaderLengthOffset = Offset;
-      if (HeaderSize == 8) {
-        ContributionSize = Data.getU32(&HeaderLengthOffset);
-      } else if (HeaderSize == 16) {
-        OldOffsetSize = 8;
-        HeaderLengthOffset += 4; // skip the dwarf64 marker
-        ContributionSize = Data.getU64(&HeaderLengthOffset);
+  DataExtractor StringData(CurStrSection, true);
+  // Validate before the single-input fast path too. Failed extraction must
+  // never keep a loop at the same offset or publish a malformed package.
+  for (const auto &Contribution : Contributions) {
+    uint64_t Offset = Contribution.Offset;
+    const uint64_t End = Offset + Contribution.Length;
+    if (End < Offset || End > Data.size())
+      return make_error<DWPError>("string offsets contribution exceeds section");
+    while (Offset < End) {
+      auto Header = parseStringOffsetsHeader(Data, Offset, Version,
+                                             Contribution.Format, End);
+      if (!Header)
+        return Header.takeError();
+      Offset += Header->HeaderSize;
+      while (Offset < Header->End) {
+        uint64_t OldOffset = Data.getUnsigned(&Offset, Header->OffsetSize);
+        uint64_t StringEnd = OldOffset;
+        const char *S = StringData.getCStr(&StringEnd);
+        if (!S)
+          return make_error<DWPError>("invalid string offset in contribution");
+        // String offsets may legally refer to a suffix of a pooled string.
+        if (!CopyOnly && !OffsetRemapping.count(OldOffset)) {
+          uint64_t NewOffset = Strings.getOffset(S, StringEnd - OldOffset);
+          OffsetRemapping[OldOffset] = NewOffset;
+          Needs64 |= NewOffset > UINT32_MAX;
+        }
       }
-      ContributionEnd = ContributionSize + HeaderLengthOffset;
-
-      StringRef HeaderBytes = Data.getBytes(&Offset, HeaderSize);
+    }
+  }
+  if (CopyOnly) {
+    for (const auto &C : Contributions)
+      Remapping[{C.Offset, C.Length}] = {C.Offset, C.Length};
+    Out.emitBytes(CurStrSection);
+    Out.switchSection(DS_StrOffsets);
+    Out.emitBytes(CurStrOffsetSection);
+    return Error::success();
+  }
+  Out.switchSection(DS_StrOffsets);
+  uint64_t WrittenSize = 0;
+  uint64_t PreviousEnd = 0;
+  for (const auto &Contribution : Contributions) {
+    // Indexed inputs may contain padding between shared table contributions.
+    Out.emitBytes(CurStrOffsetSection.slice(PreviousEnd, Contribution.Offset));
+    WrittenSize += Contribution.Offset - PreviousEnd;
+    const uint64_t NewStart = WrittenSize;
+    uint64_t Offset = Contribution.Offset;
+    const uint64_t End = Offset + Contribution.Length;
+    if (End < Offset || End > Data.size())
+      return make_error<DWPError>("string offsets contribution exceeds section");
+    while (Offset < End) {
+      auto Header = parseStringOffsetsHeader(Data, Offset, Version,
+                                             Contribution.Format, End);
+      if (!Header)
+        return Header.takeError();
+      uint64_t OldOffsetSize = Header->OffsetSize;
+      uint64_t NewOffsetSize = OldOffsetSize;
+      // DWARF4 has no table header to describe a promoted offset width.
+      if (Version >= 5 &&
+          (StrOffsetsOptValue == Dwarf64StrOffsetsPromotion::Always ||
+           (StrOffsetsOptValue != Dwarf64StrOffsetsPromotion::Disabled &&
+            Needs64)))
+        NewOffsetSize = 8;
+      StringRef HeaderBytes = Data.getBytes(&Offset, Header->HeaderSize);
       if (OldOffsetSize == 4 && NewOffsetSize == 8) {
-        // We had a DWARF32 .debug_str_offsets header, but we need to emit
-        // some string offsets that require 64 bit offsets on the .debug_str
-        // section. Emit the .debug_str_offsets header in DWARF64 format so we
-        // can emit string offsets that exceed UINT32_MAX without truncating
-        // the string offset.
-
-        // 2 bytes for DWARF version, 2 bytes pad.
-        const uint64_t VersionPadSize = 4;
-        const uint64_t NewLength =
-            (ContributionSize - VersionPadSize) * 2 + VersionPadSize;
-        // Emit the DWARF64 length that starts with a 4 byte DW_LENGTH_DWARF64
-        // value followed by the 8 byte updated length.
-        Out.emitIntValue(llvm::dwarf::DW_LENGTH_DWARF64, 4);
+        uint64_t NewLength = (Header->End - Offset) * 2 + 4;
+        Out.emitIntValue(dwarf::DW_LENGTH_DWARF64, 4);
         Out.emitIntValue(NewLength, 8);
-        // Emit DWARF version as a 2 byte integer.
         Out.emitIntValue(Version, 2);
-        // Emit 2 bytes of padding.
         Out.emitIntValue(0, 2);
-        // Update the .debug_str_offsets section length contribution for the
-        // this .dwo file.
-        for (auto &Pair : SectionLength) {
-          if (Pair.first == DW_SECT_STR_OFFSETS) {
-            Pair.second = NewLength + 12;
-            break;
-          }
-        }
+        WrittenSize += 16;
       } else {
-        // Just emit the same .debug_str_offsets header.
         Out.emitBytes(HeaderBytes);
+        WrittenSize += Header->HeaderSize;
       }
-      writeNewOffsetsTo(Out, Data, OffsetRemapping, Offset, ContributionEnd,
-                        OldOffsetSize, NewOffsetSize);
+      WrittenSize += (Header->End - Offset) / OldOffsetSize * NewOffsetSize;
+      if (Error Err = writeNewOffsetsTo(Out, Data, OffsetRemapping, Offset,
+                                        Header->End, OldOffsetSize,
+                                        NewOffsetSize))
+        return Err;
     }
-
-  } else {
-    assert(OldOffsetSize == NewOffsetSize);
-    writeNewOffsetsTo(Out, Data, OffsetRemapping, Offset, Size, OldOffsetSize,
-                      NewOffsetSize);
+    Remapping[{Contribution.Offset, Contribution.Length}] =
+        {NewStart, WrittenSize - NewStart};
+    PreviousEnd = End;
   }
+  Out.emitBytes(CurStrOffsetSection.substr(PreviousEnd));
+  WrittenSize += CurStrOffsetSection.size() - PreviousEnd;
+  for (auto &Pair : SectionLength)
+    if (Pair.first == DW_SECT_STR_OFFSETS)
+      Pair.second = WrittenSize;
+  return Error::success();
 }
 
 enum AccessField { Offset, Length };
@@ -823,9 +898,90 @@
           utostr(Version) + ")");
     }
 
-    writeStringsAndOffsets(Out, Strings, CurStrSection, CurStrOffsetSection,
-                           Header.Version, SectionLength, StrOffsetsOptValue,
-                           Inputs.size() == 1);
+    SmallVector<StringOffsetsContribution, 8> StrContributions;
+    StringOffsetsRemapping StrRemapping;
+    if (!CurCUIndexSection.empty()) {
+      // Indexed packages can share tables and leave padding between them.
+      // Include independent TU tables as well as the CU contributions.
+      auto AddStrings = [&](StringRef IndexSection, DWARFSectionKind InfoKind,
+                            StringRef InfoSection) -> Error {
+        if (IndexSection.empty())
+          return Error::success();
+        DWARFUnitIndex Index(InfoKind);
+        if (!Index.parse(DataExtractor(IndexSection, true)))
+          return make_error<DWPError>("failed to parse unit index");
+        for (const auto &E : Index.getRows()) {
+          if (!E.getContributions())
+            continue;
+          const auto *C = E.getContribution(DW_SECT_STR_OFFSETS);
+          if (!C || !C->getLength())
+            continue;
+          const auto *Unit = E.getContribution(InfoKind);
+          if (!Unit || Unit->getOffset() > InfoSection.size() ||
+              Unit->getLength() > InfoSection.size() - Unit->getOffset())
+            return make_error<DWPError>("indexed unit exceeds section");
+          DWARFDataExtractor UnitData(
+              getSubsection(InfoSection, E, InfoKind), true, 0);
+          Error Err = Error::success();
+          uint64_t UnitOffset = 0;
+          auto [Length, Format] = UnitData.getInitialLength(&UnitOffset, &Err);
+          if (Err)
+            return make_error<DWPError>("invalid indexed unit length: " +
+                                        toString(std::move(Err)));
+          if (Length > UnitData.size() - UnitOffset)
+            return make_error<DWPError>("indexed unit exceeds contribution");
+          if (C->getOffset() > CurStrOffsetSection.size() ||
+              C->getLength() > CurStrOffsetSection.size() - C->getOffset())
+            return make_error<DWPError>("indexed string contribution exceeds section");
+          StrContributions.push_back({C->getOffset(), C->getLength(), Format});
+        }
+        return Error::success();
+      };
+      if (Error Err = AddStrings(CurCUIndexSection, DW_SECT_INFO,
+                                 CurInfoSection.front()))
+        return Err;
+      if (!CurTUIndexSection.empty()) {
+        if (Header.Version < 5 && CurTypesSection.size() != 1)
+          return make_error<DWPError>("expected one indexed type section");
+        if (Error Err = AddStrings(
+                CurTUIndexSection,
+                Header.Version < 5 ? DW_SECT_EXT_TYPES : DW_SECT_INFO,
+                Header.Version < 5 ? CurTypesSection.front() :
+                                     CurInfoSection.front()))
+          return Err;
+      }
+      llvm::sort(StrContributions, [](const auto &A, const auto &B) {
+        return std::tie(A.Offset, A.Length) < std::tie(B.Offset, B.Length);
+      });
+      SmallVector<StringOffsetsContribution, 8> Distinct;
+      for (const auto &C : StrContributions) {
+        if (!Distinct.empty()) {
+          auto &P = Distinct.back();
+          uint64_t PreviousEnd = P.Offset + P.Length;
+          if (C.Offset < PreviousEnd) {
+            if (C.Offset == P.Offset && C.Length == P.Length &&
+                (Header.Version >= 5 || C.Format == P.Format))
+              continue;
+            // A DWARF4 table has no header: aligned subsets can be shared.
+            if (Header.Version < 5 && C.Format == P.Format &&
+                (C.Offset - P.Offset) % dwarf::getDwarfOffsetByteSize(C.Format) == 0) {
+              P.Length = std::max(PreviousEnd, C.Offset + C.Length) - P.Offset;
+              continue;
+            }
+            return make_error<DWPError>("incompatible overlapping string contributions");
+          }
+        }
+        Distinct.push_back(C);
+      }
+      StrContributions = std::move(Distinct);
+    } else {
+      StrContributions.push_back({0, CurStrOffsetSection.size(), Header.Format});
+    }
+    if (Error Err = writeStringsAndOffsets(
+            Out, Strings, CurStrSection, CurStrOffsetSection, Header.Version,
+            SectionLength, StrContributions, StrOffsetsOptValue,
+            Inputs.size() == 1, StrRemapping))
+      return createFileError(Input, std::move(Err));
 
     for (auto Pair : SectionLength) {
       auto Index = getContributionIndex(Pair.first, IndexVersion);
@@ -867,7 +1023,8 @@
           auto &C = Entry.Contributions[getContributionIndex(DW_SECT_INFO,
                                                              IndexVersion)];
           C.setOffset(InfoSectionOffset);
-          C.setLength(Header.Length + 4);
+          C.setLength(Header.Length +
+                      dwarf::getUnitLengthFieldByteSize(Header.Format));
 
           if (std::numeric_limits<uint32_t>::max() - InfoSectionOffset <
               C.getLength32()) {
@@ -976,8 +1133,15 @@
           continue;
         auto &C =
             NewEntry.Contributions[getContributionIndex(Kind, IndexVersion)];
-        C.setOffset(C.getOffset() + I->getOffset());
-        C.setLength(I->getLength());
+        auto Mapped = StrRemapping.find({I->getOffset(), I->getLength()});
+        if (Kind == DW_SECT_STR_OFFSETS && Header.Version >= 5 &&
+            Mapped != StrRemapping.end()) {
+          C.setOffset(C.getOffset() + Mapped->second.first);
+          C.setLength(Mapped->second.second);
+        } else {
+          C.setOffset(C.getOffset() + I->getOffset());
+          C.setLength(I->getLength());
+        }
         ++I;
       }
       unsigned Index = getContributionIndex(DW_SECT_INFO, IndexVersion);
@@ -1021,7 +1185,8 @@
       if (Error Err = addAllTypesFromDWP(
               Out, TypeIndexEntries, TUIndex, OutSection, TypeInputSection,
               CurEntry, ContributionOffsets[TypesContributionIndex],
-              TypesContributionIndex, OverflowOptValue, AnySectionOverflow))
+              TypesContributionIndex, OverflowOptValue, AnySectionOverflow,
+              StrRemapping))
         return Err;
     }
     if (AnySectionOverflow)
