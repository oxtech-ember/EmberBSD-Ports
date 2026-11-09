$NetBSD$

Allow opt-in host-visible static buffer uploads in idle offscreen frames.
Keep staging for used buffers, unfinished frames, swapchains, and external commands.

Origin: EmberBSD contributors (AI-assisted). Not submitted upstream.

--- src/gui/rhi/qrhivulkan_p.h.orig
+++ src/gui/rhi/qrhivulkan_p.h
@@ -68,6 +68,7 @@
     };
     UsageState usageState[QVK_FRAMES_IN_FLIGHT];
     int lastActiveFrameSlot = -1;
+    quint64 lastUsedOffscreenFrame = 0;
     uint generation = 0;
     friend class QRhiVulkan;
 };
@@ -892,6 +893,7 @@
                              size_t *curOfs, void *mp,
                              BufferImageCopyList *copyInfos);
     void enqueueResourceUpdates(QVkCommandBuffer *cbD, QRhiResourceUpdateBatch *resourceUpdates);
+    bool canWriteStaticBufferDirectly(QVkBuffer *bufD);
     void executeBufferHostWritesForSlot(QVkBuffer *bufD, int slot);
     void enqueueTransitionPassResources(QVkCommandBuffer *cbD);
     void recordPrimaryCommandBuffer(QVkCommandBuffer *cbD);
@@ -1064,6 +1066,10 @@
         bool cmdFenceWaitable[QVK_FRAMES_IN_FLIGHT];
         int timestampQueryIndex[QVK_FRAMES_IN_FLIGHT];
     } ofr;
+    // Offscreen frame counter for host writes to static buffers.
+    quint64 offscreenFrameSerial = 0;
+    bool offscreenFrameHasExternalCommands = false;
+    int hostStaticUploads = -1;
 
     struct TextureReadback {
         int activeFrameSlot = -1;
