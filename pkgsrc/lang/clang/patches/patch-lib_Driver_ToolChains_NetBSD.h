# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
# Preserve the NetBSD runtime and unwind policy; enable LTO for selected LLD.

--- lib/Driver/ToolChains/NetBSD.h.orig
+++ lib/Driver/ToolChains/NetBSD.h
@@ -53,6 +53,8 @@
   NetBSD(const Driver &D, const llvm::Triple &Triple,
          const llvm::opt::ArgList &Args);
 
+  bool HasNativeLLVMSupport() const override;
+
   bool IsMathErrnoDefault() const override { return false; }
   bool IsObjCNonFragileABIDefault() const override { return true; }
 
