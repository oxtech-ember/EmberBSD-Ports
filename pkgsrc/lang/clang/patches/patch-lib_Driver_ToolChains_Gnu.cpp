$NetBSD: patch-lib_Driver_ToolChains_Gnu.cpp,v 1.5 2026/03/25 22:56:25 wiz Exp $

On SunOS always use the GCC that was used to build clang.

Adapted to LLVM 23.1.2 by EmberBSD (AI-assisted); not submitted upstream.

--- lib/Driver/ToolChains/Gnu.cpp.orig
+++ lib/Driver/ToolChains/Gnu.cpp
@@ -2284,6 +2284,10 @@
     // /usr/gcc/<version> as a prefix.
 
     SmallVector<std::pair<GCCVersion, std::string>, 8> SolarisPrefixes;
+
+    // Only use compiler as configured by pkgsrc.
+    Prefixes.push_back("@GCCBASEDIR@");
+    return;
     std::string PrefixDir = concat(SysRoot, "/usr/gcc");
     std::error_code EC;
     for (llvm::vfs::directory_iterator LI = D.getVFS().dir_begin(PrefixDir, EC),
