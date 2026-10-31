$NetBSD$

--- a/boot/bootm_os.c
+++ b/boot/bootm_os.c
@@ -72,6 +72,12 @@
 	struct legacy_img_hdr *os_hdr, *hdr;
 	ulong kernel_data, kernel_len;
 	char *cmdline;
+
+#ifdef CONFIG_RISCV
+	/* RISC-V FIT kernels use the hart ID and FDT boot ABI. */
+	if (IS_ENABLED(CONFIG_FIT) && !images->legacy_hdr_valid)
+		return do_bootm_netbsd_riscv(flag, bmi);
+#endif
 
 	if (flag != BOOTM_STATE_OS_GO)
 		return 0;
