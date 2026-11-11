$NetBSD$

Allow opt-in host-visible static buffer uploads in idle offscreen frames.
Keep staging for used buffers, unfinished frames, swapchains, and external
commands. A frame counts as finished when its fence has signaled. Work that
code outside QRhi submits on its own queue with a buffer's native handle is
not covered by the frame fences; such buffers must not use this opt-in.

Allow an opt-in VMA block size for small heaps (QT_VULKAN_VMA_BLOCK_MB).
VMA otherwise uses heap/8, 128 MiB blocks on a 1 GiB unified-memory board.

Allow opt-in VMA blocks created at device setup and kept
(QT_VULKAN_VMA_MIN_BLOCKS, 1..16, for the memory type of GPU-only images),
only with QT_VULKAN_VMA_BLOCK_MB and within half of the heap budget. Each
QRhi reserves its own blocks. Otherwise each new block is allocated inside
the frame that first needs it.

Origin: EmberBSD contributors (AI-assisted). Not submitted upstream.

--- src/gui/rhi/qrhivulkan.cpp.orig
+++ src/gui/rhi/qrhivulkan.cpp
@@ -10,6 +10,19 @@
 #define VMA_STATIC_VULKAN_FUNCTIONS 0
 #define VMA_RECORDING_ENABLED 0
 #define VMA_DEDICATED_ALLOCATION 0
+// VMA sizes memory blocks as heap/8 for heaps up to 1 GiB: 128 MiB on a
+// board with 1 GiB of unified memory, mostly unused. QT_VULKAN_VMA_BLOCK_MB
+// (opt-in, 1..1024) turns that rule off and uses the given block size instead.
+// Read once for the process.
+static unsigned long long qt_vmaBlockBytes()
+{
+    static const unsigned long long bytes = [] {
+        const int mb = QT_PREPEND_NAMESPACE(qEnvironmentVariableIntValue)("QT_VULKAN_VMA_BLOCK_MB");
+        return mb > 0 && mb <= 1024 ? (unsigned long long)mb * 1024 * 1024 : 0ULL;
+    }();
+    return bytes;
+}
+#define VMA_SMALL_HEAP_MAX_SIZE (qt_vmaBlockBytes() ? 0ULL : 1024ULL * 1024 * 1024)
 QT_BEGIN_NAMESPACE
 Q_STATIC_LOGGING_CATEGORY(QRHI_LOG_VMA, "qt.rhi.vma")
 QT_END_NAMESPACE
@@ -1123,6 +1136,9 @@
         allocatorInfo.vulkanApiVersion = VK_API_VERSION_1_0;
 #endif
 
+        if (const unsigned long long blockBytes = qt_vmaBlockBytes())
+            allocatorInfo.preferredLargeHeapBlockSize = VkDeviceSize(blockBytes);
+
         VmaAllocator vmaallocator;
         VkResult err = vmaCreateAllocator(&allocatorInfo, &vmaallocator);
         if (err != VK_SUCCESS) {
@@ -1130,6 +1146,24 @@
             return false;
         }
         allocator = vmaallocator;
+
+        // Opt-in: create the blocks the application is known to grow into
+        // now, while nothing is on screen, instead of one by one inside
+        // frames later (each new block is a large zeroed kernel allocation,
+        // about 20 ms on the GE8300), and keep them. With
+        // QT_VULKAN_VMA_BLOCK_MB only (heap/8 blocks are too large to keep);
+        // at most half of the heap budget. Each QRhi reserves its own blocks.
+        const int vmaReserve = qEnvironmentVariableIntValue("QT_VULKAN_VMA_MIN_BLOCKS");
+        if (vmaReserve > 0 && vmaReserve <= 16 && qt_vmaBlockBytes() != 0) {
+            VmaAllocationCreateInfo probe = {};
+            probe.usage = VMA_MEMORY_USAGE_GPU_ONLY;
+            uint32_t typeIndex = 0;
+            VkResult res = vmaFindMemoryTypeIndex(vmaallocator, UINT32_MAX, &probe, &typeIndex);
+            if (res == VK_SUCCESS)
+                res = vmaQtReserveBlocks(vmaallocator, typeIndex, size_t(vmaReserve));
+            if (res != VK_SUCCESS)
+                qWarning("QRhiVulkan: could not reserve %d memory blocks: %d", vmaReserve, res);
+        }
     }
 
     inst->installDebugOutputFilter(qvk_debug_filter);
@@ -3082,6 +3116,8 @@
 
     prepareNewFrame(cbWrapper);
     ofr.active = true;
+    ++offscreenFrameSerial;
+    offscreenFrameHasExternalCommands = false;
 
     if (ofr.timestampQueryIndex[currentFrameSlot] >= 0) {
         quint64 timestamp[2] = { 0, 0 };
@@ -4266,6 +4302,46 @@
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
@@ -4285,6 +4361,13 @@
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
@@ -4340,6 +4423,8 @@
 
             bufD->lastActiveFrameSlot = currentFrameSlot;
 
+            bufD->lastUsedOffscreenFrame = offscreenFrameSerial;
+
             if (bufD->m_type == QRhiBuffer::Immutable) {
                 QRhiVulkan::DeferredReleaseEntry e;
                 e.type = QRhiVulkan::DeferredReleaseEntry::StagingBuffer;
@@ -4409,6 +4494,8 @@
 
                 bufD->lastActiveFrameSlot = currentFrameSlot;
 
+                bufD->lastUsedOffscreenFrame = offscreenFrameSerial;
+
                 activeBufferReadbacks.append(readback);
             }
         }
@@ -5976,6 +6063,8 @@
                 executeBufferHostWritesForSlot(bufD, currentFrameSlot);
 
             bufD->lastActiveFrameSlot = currentFrameSlot;
+
+            bufD->lastUsedOffscreenFrame = offscreenFrameSerial;
             trackedRegisterBuffer(&passResTracker, bufD, bufD->m_type == QRhiBuffer::Dynamic ? currentFrameSlot : 0,
                                   QRhiPassResourceTracker::BufUniformRead,
                                   QRhiPassResourceTracker::toPassTrackerBufferStage(b->stage));
@@ -6086,6 +6175,8 @@
                 executeBufferHostWritesForSlot(bufD, currentFrameSlot);
 
             bufD->lastActiveFrameSlot = currentFrameSlot;
+
+            bufD->lastUsedOffscreenFrame = offscreenFrameSerial;
             QRhiPassResourceTracker::BufferAccess access;
             if (b->type == QRhiShaderResourceBinding::BufferLoad)
                 access = QRhiPassResourceTracker::BufStorageLoad;
@@ -6220,6 +6311,7 @@
         QVkBuffer *bufD = QRHI_RES(QVkBuffer, bindings[i].first);
         Q_ASSERT(bufD->m_usage.testFlag(QRhiBuffer::VertexBuffer));
         bufD->lastActiveFrameSlot = currentFrameSlot;
+        bufD->lastUsedOffscreenFrame = offscreenFrameSerial;
         if (bufD->m_type == QRhiBuffer::Dynamic)
             executeBufferHostWritesForSlot(bufD, currentFrameSlot);
 
@@ -6265,6 +6357,7 @@
         QVkBuffer *ibufD = QRHI_RES(QVkBuffer, indexBuf);
         Q_ASSERT(ibufD->m_usage.testFlag(QRhiBuffer::IndexBuffer));
         ibufD->lastActiveFrameSlot = currentFrameSlot;
+        ibufD->lastUsedOffscreenFrame = offscreenFrameSerial;
         if (ibufD->m_type == QRhiBuffer::Dynamic)
             executeBufferHostWritesForSlot(ibufD, currentFrameSlot);
 
@@ -6507,6 +6600,7 @@
 
     QVkBuffer *indirectBufD = QRHI_RES(QVkBuffer, indirectBuffer);
     indirectBufD->lastActiveFrameSlot = currentFrameSlot;
+    indirectBufD->lastUsedOffscreenFrame = offscreenFrameSerial;
     if (indirectBufD->m_type == QRhiBuffer::Dynamic)
         executeBufferHostWritesForSlot(indirectBufD, currentFrameSlot);
     const int indirectBufSlot = indirectBufD->m_type == QRhiBuffer::Dynamic ? currentFrameSlot : 0;
@@ -6561,6 +6655,7 @@
 
     QVkBuffer *indirectBufD = QRHI_RES(QVkBuffer, indirectBuffer);
     indirectBufD->lastActiveFrameSlot = currentFrameSlot;
+    indirectBufD->lastUsedOffscreenFrame = offscreenFrameSerial;
     if (indirectBufD->m_type == QRhiBuffer::Dynamic)
         executeBufferHostWritesForSlot(indirectBufD, currentFrameSlot);
     const int indirectBufSlot = indirectBufD->m_type == QRhiBuffer::Dynamic ? currentFrameSlot : 0;
@@ -6703,6 +6798,10 @@
 
 void QRhiVulkan::beginExternal(QRhiCommandBuffer *cb)
 {
+    // External commands can read exported buffers without tracked bindings.
+    if (ofr.active)
+        offscreenFrameHasExternalCommands = true;
+
     QVkCommandBuffer *cbD = QRHI_RES(QVkCommandBuffer, cb);
 
     // When not in a pass, it is simple: record what we have (but do not
