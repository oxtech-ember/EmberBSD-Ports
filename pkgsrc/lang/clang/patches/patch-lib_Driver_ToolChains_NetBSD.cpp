# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
# Preserve the NetBSD runtime and unwind policy; enable LTO for selected LLD.

--- lib/Driver/ToolChains/NetBSD.cpp.orig
+++ lib/Driver/ToolChains/NetBSD.cpp
@@ -17,6 +17,7 @@
 #include "clang/Driver/SanitizerArgs.h"
 #include "clang/Options/Options.h"
 #include "llvm/Option/ArgList.h"
+#include "llvm/Support/Path.h"
 #include "llvm/Support/VirtualFileSystem.h"
 
 using namespace clang::driver;
@@ -274,6 +275,10 @@
                             options::OPT_s, options::OPT_t});
   ToolChain.AddFilePathLibArgs(Args, CmdArgs);
 
+  if (auto LTO = ToolChain.getLTOMode(Args);
+      LTO != LTOK_None && ToolChain.HasNativeLLVMSupport())
+    addLTOOptions(ToolChain, Args, CmdArgs, Output, Inputs, LTO == LTOK_Thin);
+
   bool NeedsSanitizerDeps = addSanitizerRuntimes(ToolChain, Args, CmdArgs);
   bool NeedsXRayDeps = addXRayRuntime(ToolChain, Args, CmdArgs);
   AddLinkerInputs(ToolChain, Inputs, Args, CmdArgs, JA);
@@ -309,6 +314,14 @@
 
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
@@ -341,7 +354,9 @@
       CmdArgs.push_back("-lpthread");
     CmdArgs.push_back("-lc");
 
-    if (useLibgcc) {
+    if (UseSelectedRuntime) {
+      AddRunTimeLibs(ToolChain, D, CmdArgs, Args);
+    } else if (useLibgcc) {
       if (Static) {
         // libgcc_eh depends on libc, so resolve as much as possible,
         // pull in any new requirements from libc and then get the rest
@@ -356,6 +371,8 @@
         CmdArgs.push_back("--no-as-needed");
       }
     }
+    if (Static && UseSelectedRuntime)
+      CmdArgs.push_back("--end-group");
   }
 
   if (!Args.hasArg(options::OPT_nostdlib, options::OPT_nostartfiles,
@@ -437,6 +454,13 @@
 
 Tool *NetBSD::buildLinker() const { return new tools::netbsd::Linker(*this); }
 
+bool NetBSD::HasNativeLLVMSupport() const {
+  bool IsLLD = false;
+  const std::string LinkerPath = GetLinkerPath(&IsLLD);
+  return IsLLD || llvm::sys::path::filename(LinkerPath) == "ld.lld" ||
+         llvm::sys::path::stem(LinkerPath) == "ld.lld";
+}
+
 ToolChain::CXXStdlibType NetBSD::GetDefaultCXXStdlibType() const {
   switch (getArch()) {
   case llvm::Triple::aarch64:
