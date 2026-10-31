$NetBSD$

Reserve the U-Boot stack and relocation in its actual DRAM bank.

--- a/lib/lmb.c
+++ b/lib/lmb.c
@@ -535,11 +535,11 @@
 static void lmb_reserve_uboot_region(void)
 {
 	int bank;
-	ulong end, bank_end;
-	phys_addr_t rsv_start;
+	ulong end;
+	phys_addr_t rsv_start, bank_end, rsv_size;
+	bool pram_here;
 	ulong pram = 0;
 
-	rsv_start = gd->start_addr_sp - CONFIG_STACK_SIZE;
 	end = gd->initial_relocaddr;
 
 	/*
@@ -547,7 +547,6 @@
 	 * until the original relocation address to prevent LMB from
 	 * overwriting that memory.
 	 */
-	debug("## Current stack ends at 0x%08lx\n", (ulong)rsv_start);
 
 #ifdef CFG_PRAM
 	pram = env_get_ulong("pram", 10, CFG_PRAM);
@@ -556,18 +555,28 @@
 
 	for (bank = 0; bank < CONFIG_NR_DRAM_BANKS; bank++) {
 		if (!gd->dram[bank].size ||
-		    rsv_start < gd->dram[bank].start)
+		    !gd->start_addr_sp ||
+		    gd->start_addr_sp - 1 < gd->dram[bank].start)
 			continue;
 		/* Watch out for RAM at end of address space! */
 		bank_end = gd->dram[bank].start +
 			gd->dram[bank].size - 1;
-		if (rsv_start > bank_end)
+		if (gd->start_addr_sp - 1 > bank_end)
 			continue;
-		if (bank_end > end)
+
+		/* Keep the reservation within the bank containing the stack. */
+		rsv_start = gd->start_addr_sp -
+			min_t(phys_addr_t, CONFIG_STACK_SIZE,
+			      gd->start_addr_sp - gd->dram[bank].start);
+		debug("## Current stack ends at 0x%08lx\n", (ulong)rsv_start);
+		pram_here = end > rsv_start && (phys_addr_t)end - 1 <= bank_end;
+		if (pram_here)
 			bank_end = end - 1;
-
-		lmb_reserve(rsv_start, bank_end - rsv_start - pram + 1,
-			    LMB_NOOVERWRITE);
+		rsv_size = bank_end - rsv_start + 1;
+		/* Do not shrink this bank for PRAM elsewhere or wrap the size. */
+		if (pram_here && pram < rsv_size)
+			rsv_size -= pram;
+		lmb_reserve(rsv_start, rsv_size, LMB_NOOVERWRITE);
 
 		if (gd->flags & GD_FLG_SKIP_RELOC)
 			lmb_reserve((phys_addr_t)(uintptr_t)_start,
