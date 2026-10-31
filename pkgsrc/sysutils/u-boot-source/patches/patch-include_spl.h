$NetBSD$

Declare bounded memory-mapped NOR read range.

--- a/include/spl.h
+++ b/include/spl.h
@@ -342,6 +342,14 @@
 				 ulong count, void *buf);
 
 /**
+ * spl_nor_get_bounds() - Set the readable memory-mapped NOR range
+ * @start: receives the first address
+ * @size: receives the number of bytes
+ * Return: true if bounded, false for the legacy unbounded reader
+ */
+bool spl_nor_get_bounds(ulong *start, ulong *size);
+
+/**
  * Information required to load data from a device
  *
  * @read: Function to call to read from the device
@@ -351,6 +359,11 @@
  * @no_fdt_update: true to update the FDT with any loadables that are loaded
  */
 struct spl_load_info {
+	/* Defer FIT-owned progress while a shared transport is active. */
+	bool fit_quiet;
+	bool fit_signature_failed;
+	bool fit_deprecated;
+	bool fit_fpga_loaded;
 	spl_load_reader read;
 	void *priv;
 #if IS_ENABLED(CONFIG_SPL_LOAD_BLOCK)
@@ -424,6 +437,10 @@
 {
 	load->read = h_read;
 	load->priv = priv;
+	load->fit_quiet = false;
+	load->fit_signature_failed = false;
+	load->fit_deprecated = false;
+	load->fit_fpga_loaded = false;
 	spl_set_bl_len(load, bl_len);
 	xpl_set_phase(load, IH_PHASE_NONE);
 	xpl_set_fdt_update(load, true);
