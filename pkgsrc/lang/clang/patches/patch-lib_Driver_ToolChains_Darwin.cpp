$NetBSD$

Do not enable ld64-only class selector stubs for LLD or an unknown linker.
Upstream class selector stub implementation: https://github.com/llvm/llvm-project/pull/186433
Preserve explicit compiler flags and compile-only operation.

--- lib/Driver/ToolChains/Darwin.cpp.orig
+++ lib/Driver/ToolChains/Darwin.cpp
@@ -3507,12 +3507,23 @@
       (getLinkerVersion(DriverArgs) >= VersionTuple(811, 2)))
     CC1Args.push_back("-fobjc-msgsend-selector-stubs");
 
-  // Enable objc_msgSend class selector stubs by default if the linker supports
-  // it. ld64-1250+ does, for arm64, arm64e, and arm64_32.
+  // An overridden linker path without an explicit flavor does not establish
+  // its capabilities, even when a preferred linker was configured. ld64.lld
+  // does not implement class selector stubs. Do not probe the filesystem:
+  // compile-only jobs need not have a linker.
+  const Arg *LinkerFlavor = DriverArgs.getLastArgNoClaim(options::OPT_fuse_ld_EQ);
+  const StringRef Flavor = LinkerFlavor ? LinkerFlavor->getValue()
+                                        : getDriver().getPreferredLinker();
+  const bool UnknownLinker =
+      DriverArgs.hasArgNoClaim(options::OPT_ld_path_EQ) && !LinkerFlavor;
+  const bool KnownAppleLinker =
+      !UnknownLinker && (Flavor.empty() || Flavor == "ld");
+
+  // Enable objc_msgSend class selector stubs only for known Apple ld64 1250+.
   if (!DriverArgs.hasArgNoClaim(
           options::OPT_fobjc_msgsend_class_selector_stubs,
           options::OPT_fno_objc_msgsend_class_selector_stubs) &&
-      getTriple().isAArch64() &&
+      getTriple().isAArch64() && KnownAppleLinker &&
       (getLinkerVersion(DriverArgs) >= VersionTuple(1250, 0)))
     CC1Args.push_back("-fobjc-msgsend-class-selector-stubs");
 
