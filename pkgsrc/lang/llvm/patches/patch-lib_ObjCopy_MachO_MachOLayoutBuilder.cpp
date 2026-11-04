$NetBSD$

Origin: EmberBSD (AI-assisted), refuse Mach-O linked-image header overlap.
An install-name or other load-command update can exhaust the linker's header
padding. Reject the rewrite before output instead of overwriting section data.
Not submitted upstream. SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

Handle LC_REEXPORT_DYLIB as a dylib command with no file offsets.

--- lib/ObjCopy/MachO/MachOLayoutBuilder.cpp.orig
+++ lib/ObjCopy/MachO/MachOLayoutBuilder.cpp
@@ -450,6 +450,7 @@
     case MachO::LC_ID_DYLIB:
     case MachO::LC_LOAD_DYLIB:
     case MachO::LC_LOAD_WEAK_DYLIB:
+    case MachO::LC_REEXPORT_DYLIB:
     case MachO::LC_UUID:
     case MachO::LC_SOURCE_VERSION:
     case MachO::LC_THREAD:
@@ -477,6 +478,22 @@
   constructStringTable();
   updateSymbolIndexes();
   uint64_t Offset = layoutSegments();
+  // Linked images keep their section addresses and file offsets. Growing a
+  // load command can exhaust the padding reserved by the linker; writing the
+  // enlarged header would then overwrite section contents. Relocatable objects
+  // are laid out after the new header and do not have this restriction.
+  if (O.Header.FileType != MachO::HeaderFileType::MH_OBJECT) {
+    const uint64_t HeaderEnd =
+        (Is64Bit ? sizeof(MachO::mach_header_64) : sizeof(MachO::mach_header)) +
+        uint64_t(O.Header.SizeOfCmds);
+    for (const LoadCommand &LC : O.LoadCommands)
+      for (const auto &Sec : LC.Sections)
+        if (Sec->hasValidOffset() && Sec->Size && Sec->Offset < HeaderEnd)
+          return createStringError(
+              llvm::errc::invalid_argument,
+              "not enough space for load commands; relink with "
+              "-headerpad_max_install_names");
+  }
   Offset = layoutRelocations(Offset);
   return layoutTail(Offset);
 }
