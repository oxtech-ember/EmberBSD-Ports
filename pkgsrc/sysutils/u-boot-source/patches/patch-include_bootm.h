$NetBSD$

--- a/include/bootm.h
+++ b/include/bootm.h
@@ -81,6 +81,9 @@
 typedef int boot_os_fn(int flag, struct bootm_info *bmi);
 
 extern boot_os_fn do_bootm_linux;
+#ifdef CONFIG_RISCV
+extern boot_os_fn do_bootm_netbsd_riscv;
+#endif
 extern boot_os_fn do_bootm_vxworks;
 
 int do_bootelf(struct cmd_tbl *cmdtp, int fglag, int argc, char *const argv[]);
