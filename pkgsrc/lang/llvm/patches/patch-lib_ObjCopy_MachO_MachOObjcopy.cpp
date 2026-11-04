$NetBSD$

Origin: EmberBSD (AI-assisted), handle Mach-O reexport install names.
Not submitted upstream. SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

--- lib/ObjCopy/MachO/MachOObjcopy.cpp.orig
+++ lib/ObjCopy/MachO/MachOObjcopy.cpp
@@ -34,12 +34,12 @@
 
 #ifndef NDEBUG
 static bool isLoadCommandWithPayloadString(const LoadCommand &LC) {
-  // TODO: Add support for LC_REEXPORT_DYLIB, LC_LOAD_UPWARD_DYLIB and
-  // LC_LAZY_LOAD_DYLIB
+  // TODO: Add support for LC_LOAD_UPWARD_DYLIB and LC_LAZY_LOAD_DYLIB.
   return LC.MachOLoadCommand.load_command_data.cmd == MachO::LC_RPATH ||
          LC.MachOLoadCommand.load_command_data.cmd == MachO::LC_ID_DYLIB ||
          LC.MachOLoadCommand.load_command_data.cmd == MachO::LC_LOAD_DYLIB ||
-         LC.MachOLoadCommand.load_command_data.cmd == MachO::LC_LOAD_WEAK_DYLIB;
+         LC.MachOLoadCommand.load_command_data.cmd == MachO::LC_LOAD_WEAK_DYLIB ||
+         LC.MachOLoadCommand.load_command_data.cmd == MachO::LC_REEXPORT_DYLIB;
 }
 #endif
 
@@ -259,10 +259,11 @@
       break;
     }
 
-    // TODO: Add LC_REEXPORT_DYLIB, LC_LAZY_LOAD_DYLIB, and LC_LOAD_UPWARD_DYLIB
+    // TODO: Add LC_LAZY_LOAD_DYLIB and LC_LOAD_UPWARD_DYLIB
     // here once llvm-objcopy supports them.
     case MachO::LC_LOAD_DYLIB:
     case MachO::LC_LOAD_WEAK_DYLIB:
+    case MachO::LC_REEXPORT_DYLIB:
       StringRef InstallName = getPayloadString(LC);
       StringRef NewInstallName =
           MachOConfig.InstallNamesToUpdate.lookup(InstallName);
