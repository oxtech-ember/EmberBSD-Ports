$NetBSD$

Use the line table format for DW_FORM_line_strp offsets. GCC -gdwarf64 can
emit a DWARF64 CU with a DWARF32 line table; the original BFD reader used
the CU width and read adjacent fields as one string offset. Leave indexed
string resolution tied to the CU.

Origin: EmberBSD (AI-assisted), reproduced with GCC 16.2/Binutils 2.47.
Not submitted or accepted upstream.
Reference: DWARF 5 section 6.2.4, https://dwarfstd.org/doc/DWARF5.pdf

--- bfd/dwarf2.c.orig
+++ bfd/dwarf2.c
@@ -924,20 +924,21 @@
 static char *
 read_indirect_line_string (struct comp_unit *unit,
 			   bfd_byte **ptr,
-			   bfd_byte *buf_end)
+			   bfd_byte *buf_end,
+			   unsigned int offset_size)
 {
   uint64_t offset;
   struct dwarf2_debug *stash = unit->stash;
   struct dwarf2_debug_file *file = unit->file;
   char *str;
 
-  if (unit->offset_size > (size_t) (buf_end - *ptr))
+  if (offset_size > (size_t) (buf_end - *ptr))
     {
       *ptr = buf_end;
       return NULL;
     }
 
-  if (unit->offset_size == 4)
+  if (offset_size == 4)
     offset = read_4_bytes (unit->abfd, ptr, buf_end);
   else
     offset = read_8_bytes (unit->abfd, ptr, buf_end);
@@ -1591,7 +1592,8 @@
       attr->u.str = read_indirect_string (unit, &info_ptr, info_ptr_end);
       break;
     case DW_FORM_line_strp:
-      attr->u.str = read_indirect_line_string (unit, &info_ptr, info_ptr_end);
+      attr->u.str = read_indirect_line_string (unit, &info_ptr, info_ptr_end,
+					       unit->offset_size);
       break;
     case DW_FORM_GNU_strp_alt:
       attr->u.str = read_alt_indirect_string (unit, &info_ptr, info_ptr_end);
@@ -2588,6 +2590,7 @@
 static bool
 read_formatted_entries (struct comp_unit *unit, bfd_byte **bufp,
 			bfd_byte *buf_end, struct line_info_table *table,
+			unsigned int offset_size,
 			bool (*callback) (struct line_info_table *table,
 					  char *cur_file,
 					  unsigned int dir,
@@ -2667,7 +2670,13 @@
 	    }
 
 	  form = _bfd_safe_read_leb128 (abfd, &format, false, buf_end);
-	  buf = read_attribute_value (&attr, form, 0, unit, buf, buf_end);
+	  /* The line table can use a different DWARF format from its CU.
+	     Indexed strings still use the CU's .debug_str_offsets format.  */
+	  if (form == DW_FORM_line_strp)
+	    attr.u.str = read_indirect_line_string (unit, &buf, buf_end,
+						  offset_size);
+	  else
+	    buf = read_attribute_value (&attr, form, 0, unit, buf, buf_end);
 	  if (buf == NULL)
 	    return false;
 	  switch (form)
@@ -2866,12 +2875,12 @@
   if (lh.version >= 5)
     {
       /* Read directory table.  */
-      if (!read_formatted_entries (unit, &line_ptr, line_end, table,
+      if (!read_formatted_entries (unit, &line_ptr, line_end, table, offset_size,
 				   line_info_add_include_dir_stub))
 	goto fail;
 
       /* Read file name table.  */
-      if (!read_formatted_entries (unit, &line_ptr, line_end, table,
+      if (!read_formatted_entries (unit, &line_ptr, line_end, table, offset_size,
 				   line_info_add_file_name))
 	goto fail;
       table->use_dir_and_file_0 = true;
