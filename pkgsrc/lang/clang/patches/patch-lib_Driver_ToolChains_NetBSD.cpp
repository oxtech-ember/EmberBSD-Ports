# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
# Honor explicitly selected runtimes for the EmberBSD SDK. Preserve the
# upstream NetBSD base ABI when no runtime is selected. The common helper
# handles compiler-rt/libgcc, unwindlib and static/shared selection. Repeat
# runtimes around libc as in FreeBSD/OpenBSD; do not copy their hardcoded
# base runtime names or alter native Darwin defaults.

--- lib/Driver/ToolChains/NetBSD.cpp.orig
+++ lib/Driver/ToolChains/NetBSD.cpp
@@ -284,6 +284,10 @@
     CmdArgs.push_back(Args.MakeArgString(ToolChain.getCompilerRTPath()));
   }
 
+  // The base system historically provides the runtime on several targets.
+  // An explicitly selected runtime must instead use the common driver policy.
+  const bool UseSelectedRuntime =
+      Args.hasArg(options::OPT_rtlib_EQ, options::OPT_unwindlib_EQ);
   bool useLibgcc = true;
   switch (ToolChain.getArch()) {
   case llvm::Triple::aarch64:
@@ -337,11 +341,16 @@
       linkSanitizerRuntimeDeps(ToolChain, Args, CmdArgs);
     if (NeedsXRayDeps)
       linkXRayRuntimeDeps(ToolChain, Args, CmdArgs);
+    // Repeat the runtime around libc, as the BSD static link order requires.
+    if (UseSelectedRuntime)
+      AddRunTimeLibs(ToolChain, D, CmdArgs, Args);
     if (Args.hasArg(options::OPT_pthread))
       CmdArgs.push_back("-lpthread");
     CmdArgs.push_back("-lc");
 
-    if (useLibgcc) {
+    if (UseSelectedRuntime) {
+      AddRunTimeLibs(ToolChain, D, CmdArgs, Args);
+    } else if (useLibgcc) {
       if (Static) {
         // libgcc_eh depends on libc, so resolve as much as possible,
         // pull in any new requirements from libc and then get the rest
