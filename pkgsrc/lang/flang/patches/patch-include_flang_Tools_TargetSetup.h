$NetBSD$

REAL(16) on targets whose long double is IEEE binary128, such as
NetBSD/aarch64, also when the build machine has no such type.
https://github.com/llvm/llvm-project/issues/160060

--- include/flang/Tools/TargetSetup.h.orig
+++ include/flang/Tools/TargetSetup.h
@@ -67,7 +67,14 @@
   constexpr bool f128Support = false;
 #endif
 
-  if constexpr (!f128Support) {
+  // The checks above describe the build machine. A target whose C long
+  // double is IEEE binary128 has REAL(16) whatever the build machine has:
+  // the Flang-RT built for it implements kind 16 with the libm long double
+  // functions (HAS_LDBL128). AArch64 ELF targets use binary128 long double
+  // (AAPCS64); Darwin and Windows use double.
+  const bool targetLdbl128{targetTriple.isAArch64() &&
+      !targetTriple.isOSDarwin() && !targetTriple.isOSWindows()};
+  if (!f128Support && !targetLdbl128) {
     targetCharacteristics.DisableType(Fortran::common::TypeCategory::Real, 16);
     targetCharacteristics.DisableType(
         Fortran::common::TypeCategory::Complex, 16);
