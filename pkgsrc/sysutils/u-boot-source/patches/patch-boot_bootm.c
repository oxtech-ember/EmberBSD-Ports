$NetBSD$

--- a/boot/bootm.c
+++ b/boot/bootm.c
@@ -564,6 +564,8 @@
 	     images.os.type == IH_TYPE_KERNEL_NOLOAD ||
 	     images.os.type == IH_TYPE_MULTI) &&
 	    (images.os.os == IH_OS_LINUX || images.os.os == IH_OS_VXWORKS ||
+	     (IS_ENABLED(CONFIG_RISCV) && IS_ENABLED(CONFIG_FIT) &&
+	      !images.legacy_hdr_valid && images.os.os == IH_OS_NETBSD) ||
 	     images.os.os == IH_OS_EFI || images.os.os == IH_OS_TEE ||
 	     images.os.os == IH_OS_ELF)) {
 		return bootm_find_images(img_addr, conf_ramdisk, conf_fdt, 0,
