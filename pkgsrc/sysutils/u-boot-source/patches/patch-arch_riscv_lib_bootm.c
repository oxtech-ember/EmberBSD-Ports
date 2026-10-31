$NetBSD$

--- a/arch/riscv/lib/bootm.c
+++ b/arch/riscv/lib/bootm.c
@@ -25,7 +25,7 @@
 
 DECLARE_GLOBAL_DATA_PTR;
 
-static void boot_prep_linux(struct bootm_headers *images)
+static void boot_prep_riscv_fdt(struct bootm_headers *images)
 {
 	if (CONFIG_IS_ENABLED(OF_LIBFDT) && IS_ENABLED(CONFIG_LMB) && images->ft_len) {
 		debug("using: FDT\n");
@@ -39,7 +39,7 @@
 	}
 }
 
-static void boot_jump_linux(struct bootm_headers *images, int flag)
+static void boot_jump_riscv_fdt(struct bootm_headers *images, int flag)
 {
 	void (*kernel)(ulong hart, void *dtb);
 #ifdef CONFIG_SMP
@@ -69,7 +69,7 @@
 	}
 }
 
-int do_bootm_linux(int flag, struct bootm_info *bmi)
+static int do_bootm_riscv_fdt(int flag, struct bootm_info *bmi)
 {
 	struct bootm_headers *images = bmi->images;
 
@@ -78,21 +78,32 @@
 		return -1;
 
 	if (flag & BOOTM_STATE_OS_PREP) {
-		boot_prep_linux(images);
+		boot_prep_riscv_fdt(images);
 		return 0;
 	}
 
 	if (flag & (BOOTM_STATE_OS_GO | BOOTM_STATE_OS_FAKE_GO)) {
-		boot_jump_linux(images, flag);
+		boot_jump_riscv_fdt(images, flag);
 		return 0;
 	}
 
-	boot_prep_linux(images);
-	boot_jump_linux(images, flag);
+	boot_prep_riscv_fdt(images);
+	boot_jump_riscv_fdt(images, flag);
 	return 0;
+}
+
+int do_bootm_linux(int flag, struct bootm_info *bmi)
+{
+	return do_bootm_riscv_fdt(flag, bmi);
 }
 
 int do_bootm_vxworks(int flag, struct bootm_info *bmi)
 {
-	return do_bootm_linux(flag, bmi);
+	return do_bootm_riscv_fdt(flag, bmi);
 }
+
+/* FIT NetBSD kernels use the standard RISC-V hart/FDT entry ABI. */
+int do_bootm_netbsd_riscv(int flag, struct bootm_info *bmi)
+{
+	return do_bootm_riscv_fdt(flag, bmi);
+}
