Return allocation failure before copying into a null message.

An exhausted valid target arena can make upb_Message_New return NULL.
upb_Message_DeepClone documents failure through a NULL result.
The installed-C regression reproduces an invalid write without this check.

Origin: EmberBSD local adaptation. Prepared with AI assistance.
Upstream status: not submitted.

--- upb/message/copy.c.orig
+++ upb/message/copy.c
@@ -295,6 +295,7 @@
 upb_Message* upb_Message_DeepClone(const upb_Message* msg,
                                    const upb_MiniTable* m, upb_Arena* arena) {
   upb_Message* clone = upb_Message_New(m, arena);
+  if (clone == NULL) return NULL;
   return _upb_Message_Copy(clone, msg, m, arena);
 }
 
