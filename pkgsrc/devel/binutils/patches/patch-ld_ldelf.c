$NetBSD$

Load a DT_NEEDED shared object only once when an LTO plugin is active.
ld loads DT_NEEDED entries before the plugin "all symbols read" hook
(PR ld/28849) and again after all input files are opened. The first
BFD leaves the input list, but its symbols stay in the hash table. The
second copy then makes each definition of the first copy a reference.
For a .gnu.warning.SYMBOL section, that reference emits the warning.
With --copy-dt-needed-entries and --fatal-warnings, a link that only
uses libm fails on the warnings of libc, which libm needs. Use the BFD
of the first pass again.

Origin: EmberBSD (AI-assisted), reproduced with GCC 16.2/Binutils 2.47
and upstream master. Not submitted or accepted upstream.

--- ld/ldelf.c.orig
+++ ld/ldelf.c
@@ -60,6 +60,10 @@ const char *ldelf_emit_note_fdo_package_metadata;
 
 static struct bfd_link_needed_list *global_needed;
 static lang_input_statement_type *global_found;
+/* Shared objects loaded for DT_NEEDED entries before the plugin
+   "all symbols read" hook.  */
+static bfd **plugin_needed_bfds;
+static size_t plugin_needed_count;
 static struct stat global_stat;
 static struct bfd_link_needed_list *global_vercheck_needed;
 static bool global_vercheck_failed;
@@ -386,6 +390,35 @@ ldelf_try_needed (struct dt_needed *needed, int force, int is_linux)
       return true;
     }
 
+  /* The symbols of a shared object loaded before the plugin "all
+     symbols read" hook are still in the hash table.  Use that BFD
+     again.  A second copy would make the definitions of the first
+     copy look like references, which emits link-time warnings.  */
+  if (!elf_hash_table (&link_info)->handling_dt_needed)
+    {
+      size_t i;
+
+      for (i = 0; i < plugin_needed_count; i++)
+	{
+	  struct stat st;
+	  bfd *pbfd = plugin_needed_bfds[i];
+
+	  if (pbfd != NULL
+	      && bfd_stat (pbfd, &st) == 0
+	      && st.st_dev == global_stat.st_dev
+	      && st.st_ino == global_stat.st_ino
+	      && st.st_ino != 0)
+	    {
+	      bfd_close (abfd);
+	      plugin_needed_bfds[i] = NULL;
+	      pbfd->link.next = NULL;
+	      *link_info.input_bfds_tail = pbfd;
+	      link_info.input_bfds_tail = &pbfd->link.next;
+	      return true;
+	    }
+	}
+    }
+
   /* Specify the soname to use.  */
   bfd_elf_set_dt_needed_name (abfd, soname);
 
@@ -1209,6 +1242,15 @@ ldelf_handle_dt_needed (struct elf_link_hash_table *htab,
 	    fatal (_("%P: failed to add DT_NEEDED dynamic tag\n"));
 	}
 
+  if (htab->handling_dt_needed)
+    for (abfd = *save_input_bfd_tail; abfd != NULL; abfd = abfd->link.next)
+      {
+	plugin_needed_bfds
+	  = xrealloc (plugin_needed_bfds,
+		      (plugin_needed_count + 1) * sizeof (*plugin_needed_bfds));
+	plugin_needed_bfds[plugin_needed_count++] = abfd;
+      }
+
   link_info.input_bfds_tail = save_input_bfd_tail;
   *save_input_bfd_tail = NULL;
 }
