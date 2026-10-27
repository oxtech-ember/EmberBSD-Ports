# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
# Honor explicit runtime and unwind selections with the common driver policy.
# Group static runtime dependencies; retain unselected NetBSD base defaults.

--- lib/Driver/ToolChains/NetBSD.cpp.orig
+++ lib/Driver/ToolChains/NetBSD.cpp
@@ -309,6 +309,14 @@
 
   if (!Args.hasArg(options::OPT_nostdlib, options::OPT_nodefaultlibs,
                    options::OPT_r)) {
+    const bool UseSelectedRuntime =
+        Args.hasArg(options::OPT_rtlib_EQ, options::OPT_unwindlib_EQ) ||
+        ToolChain.GetRuntimeLibType(Args) == ToolChain::RLT_CompilerRT;
+    // Static C++, unwind, builtins and libc can refer back to each other.
+    // Resolve the selected runtime set together, retaining OS CRT ownership.
+    if (Static && UseSelectedRuntime)
+      CmdArgs.push_back("--start-group");
+
     // Use the static OpenMP runtime with -static-openmp
     bool StaticOpenMP = Args.hasArg(options::OPT_static_openmp) && !Static;
     addOpenMPRuntime(C, CmdArgs, ToolChain, Args, StaticOpenMP);
@@ -341,7 +349,9 @@
       CmdArgs.push_back("-lpthread");
     CmdArgs.push_back("-lc");
 
-    if (useLibgcc) {
+    if (UseSelectedRuntime) {
+      AddRunTimeLibs(ToolChain, D, CmdArgs, Args);
+    } else if (useLibgcc) {
       if (Static) {
         // libgcc_eh depends on libc, so resolve as much as possible,
         // pull in any new requirements from libc and then get the rest
@@ -356,6 +366,8 @@
         CmdArgs.push_back("--no-as-needed");
       }
     }
+    if (Static && UseSelectedRuntime)
+      CmdArgs.push_back("--end-group");
   }
 
   if (!Args.hasArg(options::OPT_nostdlib, options::OPT_nostartfiles,
