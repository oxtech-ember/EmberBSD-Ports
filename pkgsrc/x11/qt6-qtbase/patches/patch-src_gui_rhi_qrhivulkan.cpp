$NetBSD$

Allow opt-in host-visible static buffer uploads in idle offscreen frames.
Keep staging for used buffers, unfinished frames, swapchains, and external
commands. A frame counts as finished when its fence has signaled. Work that
code outside QRhi submits on its own queue with a buffer's native handle is
not covered by the frame fences; such buffers must not use this opt-in.

Origin: EmberBSD contributors (AI-assisted). Not submitted upstream.

--- src/gui/rhi/qrhivulkan.cpp.orig
+++ src/gui/rhi/qrhivulkan.cpp
@@ -3082,6 +3082,8 @@
 
     prepareNewFrame(cbWrapper);
     ofr.active = true;
+    ++offscreenFrameSerial;
+    offscreenFrameHasExternalCommands = false;
 
     if (ofr.timestampQueryIndex[currentFrameSlot] >= 0) {
         quint64 timestamp[2] = { 0, 0 };
@@ -4266,6 +4268,46 @@
 #endif // VK_EXT_device_fault
 }
 
+// Opt-in for unified memory devices: write a static buffer directly during an
+// offscreen frame when every submitted frame has finished and this frame has
+// not used the buffer yet, so the write cannot race GPU reads or reorder
+// commands.
+bool QRhiVulkan::canWriteStaticBufferDirectly(QVkBuffer *bufD)
+{
+    if (hostStaticUploads < 0)
+        hostStaticUploads = qEnvironmentVariableIntValue("QT_VULKAN_HOST_STATIC_UPLOADS") > 0 ? 1 : 0;
+    // Mixed swapchain frames can still read another frame slot. Use staging.
+    if (!hostStaticUploads || !ofr.active || !swapchains.isEmpty()
+        || offscreenFrameHasExternalCommands
+        || bufD->lastUsedOffscreenFrame == offscreenFrameSerial)
+        return false;
+    // A frame slot still waitable may have finished already: with page-flip
+    // pacing the previous frame is on screen, so its GPU work is done. Ask the
+    // fence once per frame instead of treating every waitable slot as busy,
+    // which sent nearly every upload through a staging copy.
+    static thread_local const QRhiVulkan *idleRhi = nullptr;
+    static thread_local quint64 idleSerial = 0;
+    static thread_local bool idle = false;
+    if (idleRhi != this || idleSerial != offscreenFrameSerial) {
+        idle = true;
+        for (int i = 0; i < QVK_FRAMES_IN_FLIGHT; ++i) {
+            if (i != currentFrameSlot && ofr.cmdFenceWaitable[i]
+                && df->vkGetFenceStatus(dev, ofr.cmdFence[i]) != VK_SUCCESS) {
+                idle = false;
+                break;
+            }
+        }
+        idleRhi = this;
+        idleSerial = offscreenFrameSerial;
+    }
+    if (!idle)
+        return false;
+    VkMemoryPropertyFlags flags = 0;
+    vmaGetAllocationMemoryProperties(toVmaAllocator(allocator),
+                                     toVmaAllocation(bufD->allocations[0]), &flags);
+    return (flags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) != 0;
+}
+
 void QRhiVulkan::enqueueResourceUpdates(QVkCommandBuffer *cbD, QRhiResourceUpdateBatch *resourceUpdates)
 {
     QRhiResourceUpdateBatchPrivate *ud = QRhiResourceUpdateBatchPrivate::get(resourceUpdates);
@@ -4285,6 +4327,13 @@
             Q_ASSERT(bufD->m_type != QRhiBuffer::Dynamic);
             Q_ASSERT(u.offset + u.data.size() <= bufD->m_size);
 
+            // Host-visible device memory needs no staging copy when no GPU work can read it.
+            if (canWriteStaticBufferDirectly(bufD)
+                && vmaCopyMemoryToAllocation(toVmaAllocator(allocator), u.data.constData(),
+                                             toVmaAllocation(bufD->allocations[0]),
+                                             u.offset, u.data.size()) == VK_SUCCESS)
+                continue;
+
             if (!bufD->stagingBuffers[currentFrameSlot]) {
                 VkBufferCreateInfo bufferInfo = {};
                 bufferInfo.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
@@ -4340,6 +4389,8 @@
 
             bufD->lastActiveFrameSlot = currentFrameSlot;
 
+            bufD->lastUsedOffscreenFrame = offscreenFrameSerial;
+
             if (bufD->m_type == QRhiBuffer::Immutable) {
                 QRhiVulkan::DeferredReleaseEntry e;
                 e.type = QRhiVulkan::DeferredReleaseEntry::StagingBuffer;
@@ -4409,6 +4460,8 @@
 
                 bufD->lastActiveFrameSlot = currentFrameSlot;
 
+                bufD->lastUsedOffscreenFrame = offscreenFrameSerial;
+
                 activeBufferReadbacks.append(readback);
             }
         }
@@ -5976,6 +6029,8 @@
                 executeBufferHostWritesForSlot(bufD, currentFrameSlot);
 
             bufD->lastActiveFrameSlot = currentFrameSlot;
+
+            bufD->lastUsedOffscreenFrame = offscreenFrameSerial;
             trackedRegisterBuffer(&passResTracker, bufD, bufD->m_type == QRhiBuffer::Dynamic ? currentFrameSlot : 0,
                                   QRhiPassResourceTracker::BufUniformRead,
                                   QRhiPassResourceTracker::toPassTrackerBufferStage(b->stage));
@@ -6086,6 +6141,8 @@
                 executeBufferHostWritesForSlot(bufD, currentFrameSlot);
 
             bufD->lastActiveFrameSlot = currentFrameSlot;
+
+            bufD->lastUsedOffscreenFrame = offscreenFrameSerial;
             QRhiPassResourceTracker::BufferAccess access;
             if (b->type == QRhiShaderResourceBinding::BufferLoad)
                 access = QRhiPassResourceTracker::BufStorageLoad;
@@ -6220,6 +6277,7 @@
         QVkBuffer *bufD = QRHI_RES(QVkBuffer, bindings[i].first);
         Q_ASSERT(bufD->m_usage.testFlag(QRhiBuffer::VertexBuffer));
         bufD->lastActiveFrameSlot = currentFrameSlot;
+        bufD->lastUsedOffscreenFrame = offscreenFrameSerial;
         if (bufD->m_type == QRhiBuffer::Dynamic)
             executeBufferHostWritesForSlot(bufD, currentFrameSlot);
 
@@ -6265,6 +6323,7 @@
         QVkBuffer *ibufD = QRHI_RES(QVkBuffer, indexBuf);
         Q_ASSERT(ibufD->m_usage.testFlag(QRhiBuffer::IndexBuffer));
         ibufD->lastActiveFrameSlot = currentFrameSlot;
+        ibufD->lastUsedOffscreenFrame = offscreenFrameSerial;
         if (ibufD->m_type == QRhiBuffer::Dynamic)
             executeBufferHostWritesForSlot(ibufD, currentFrameSlot);
 
@@ -6507,6 +6566,7 @@
 
     QVkBuffer *indirectBufD = QRHI_RES(QVkBuffer, indirectBuffer);
     indirectBufD->lastActiveFrameSlot = currentFrameSlot;
+    indirectBufD->lastUsedOffscreenFrame = offscreenFrameSerial;
     if (indirectBufD->m_type == QRhiBuffer::Dynamic)
         executeBufferHostWritesForSlot(indirectBufD, currentFrameSlot);
     const int indirectBufSlot = indirectBufD->m_type == QRhiBuffer::Dynamic ? currentFrameSlot : 0;
@@ -6561,6 +6621,7 @@
 
     QVkBuffer *indirectBufD = QRHI_RES(QVkBuffer, indirectBuffer);
     indirectBufD->lastActiveFrameSlot = currentFrameSlot;
+    indirectBufD->lastUsedOffscreenFrame = offscreenFrameSerial;
     if (indirectBufD->m_type == QRhiBuffer::Dynamic)
         executeBufferHostWritesForSlot(indirectBufD, currentFrameSlot);
     const int indirectBufSlot = indirectBufD->m_type == QRhiBuffer::Dynamic ? currentFrameSlot : 0;
@@ -6703,6 +6764,10 @@
 
 void QRhiVulkan::beginExternal(QRhiCommandBuffer *cb)
 {
+    // External commands can read exported buffers without tracked bindings.
+    if (ofr.active)
+        offscreenFrameHasExternalCommands = true;
+
     QVkCommandBuffer *cbD = QRHI_RES(QVkCommandBuffer, cb);
 
     // When not in a pass, it is simple: record what we have (but do not
