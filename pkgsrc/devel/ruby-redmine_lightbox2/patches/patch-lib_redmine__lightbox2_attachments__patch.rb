$NetBSD$

Zeitwerk expects RedmineLightbox2::AttachmentsPatch in this path; Rails 7
removed unloadable.

--- lib/redmine_lightbox2/attachments_patch.rb.orig
+++ lib/redmine_lightbox2/attachments_patch.rb
@@ -0,0 +1,15 @@
+module RedmineLightbox2
+  # Adds the inline download that the PDF preview opens in the lightbox.
+  module AttachmentsPatch
+    def download_inline
+      # apply the before actions of AttachmentsController#download
+      find_attachment
+      file_readable
+      read_authorize
+
+      send_file @attachment.diskfile, :filename => filename_for_content_disposition(@attachment.filename),
+                :type => detect_content_type(@attachment),
+                :disposition => 'inline'
+    end
+  end
+end
