$NetBSD$

ARM targets that set a default FPU do not read these option pointers.
Mark them like the other target-specific FPU variables in this file.
Clang 23 can then build GAS with its normal warning checks.

Origin: EmberBSD (AI-assisted), for GNU Binutils 2.47.

--- gas/config/tc-arm.c.orig
+++ gas/config/tc-arm.c
@@ -172,12 +172,12 @@
 /* CPU, extension and FPU feature bits selected by -mcpu.  */
 static const arm_feature_set *mcpu_cpu_opt = NULL;
 static arm_feature_set *mcpu_ext_opt = NULL;
-static const arm_feature_set *mcpu_fpu_opt = NULL;
+static const arm_feature_set *mcpu_fpu_opt ATTRIBUTE_UNUSED = NULL;
 
 /* CPU, extension and FPU feature bits selected by -march.  */
 static const arm_feature_set *march_cpu_opt = NULL;
 static arm_feature_set *march_ext_opt = NULL;
-static const arm_feature_set *march_fpu_opt = NULL;
+static const arm_feature_set *march_fpu_opt ATTRIBUTE_UNUSED = NULL;
 
 /* Feature bits selected by -mfpu.  */
 static const arm_feature_set *mfpu_opt = NULL;
