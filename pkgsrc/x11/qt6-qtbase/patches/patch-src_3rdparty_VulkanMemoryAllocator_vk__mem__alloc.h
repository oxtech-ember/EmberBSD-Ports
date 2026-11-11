$NetBSD$

Add vmaQtReserveBlocks(): create blocks of the preferred size in the default
pool of one memory type now and never free that pool below that count.
All or nothing, within half of the heap budget.
QRhiVulkan uses it for QT_VULKAN_VMA_MIN_BLOCKS.

Origin: EmberBSD contributors (AI-assisted). Not submitted upstream.

--- src/3rdparty/VulkanMemoryAllocator/vk_mem_alloc.h.orig
+++ src/3rdparty/VulkanMemoryAllocator/vk_mem_alloc.h
@@ -9846,6 +9846,7 @@
     VMA_RW_MUTEX &GetMutex() { return m_Mutex; }
 
     VkResult CreateMinBlocks();
+    VkResult QtReserveBlocks(size_t count);
     void AddStatistics(VmaStatistics& inoutStats);
     void AddDetailedStatistics(VmaDetailedStatistics& inoutStats);
     bool IsEmpty();
@@ -9872,7 +9873,7 @@
     const VmaPool m_hParentPool;
     const uint32_t m_MemoryTypeIndex;
     const VkDeviceSize m_PreferredBlockSize;
-    const size_t m_MinBlockCount;
+    size_t m_MinBlockCount;
     const size_t m_MaxBlockCount;
     const VkDeviceSize m_BufferImageGranularity;
     const bool m_ExplicitBlockSize;
@@ -11317,6 +11318,45 @@
     }
 }
 
+// Qt (EmberBSD): create blocks up to count now and never free below it.
+// Reserved blocks may use at most half of the heap budget. All or nothing:
+// on failure the blocks created here are destroyed and the minimum is kept.
+VkResult VmaBlockVector::QtReserveBlocks(size_t count)
+{
+    VmaMutexLockWrite lock(m_Mutex, m_hAllocator->m_UseMutex);
+    const uint32_t heapIndex = m_hAllocator->MemoryTypeIndexToHeapIndex(m_MemoryTypeIndex);
+    const size_t before = m_Blocks.size();
+    VkResult res = VK_SUCCESS;
+    while (m_Blocks.size() < count)
+    {
+        VmaBudget budget = {};
+        m_hAllocator->GetHeapBudgets(&budget, heapIndex, 1);
+        if (budget.usage + m_PreferredBlockSize > budget.budget / 2)
+        {
+            res = VK_ERROR_OUT_OF_DEVICE_MEMORY;
+            break;
+        }
+        res = CreateBlock(m_PreferredBlockSize, VMA_NULL);
+        if (res != VK_SUCCESS)
+            break;
+    }
+    if (res != VK_SUCCESS)
+    {
+        while (m_Blocks.size() > before)
+        {
+            VmaDeviceMemoryBlock* pBlock = m_Blocks.back();
+            VMA_ASSERT(pBlock->m_pMetadata->IsEmpty());
+            m_Blocks.pop_back();
+            pBlock->Destroy(m_hAllocator);
+            vma_delete(m_hAllocator, pBlock);
+        }
+        return res;
+    }
+    if (m_Blocks.size() > m_MinBlockCount)
+        m_MinBlockCount = m_Blocks.size();
+    return VK_SUCCESS;
+}
+
 VkResult VmaBlockVector::CreateMinBlocks()
 {
     for (size_t i = 0; i < m_MinBlockCount; ++i)
@@ -15545,6 +15585,21 @@
     return allocator->FindMemoryTypeIndex(memoryTypeBits, pAllocationCreateInfo, VmaBufferImageUsage::UNKNOWN, pMemoryTypeIndex);
 }
 
+// Qt (EmberBSD): keep at least blockCount blocks of the preferred size in
+// the default pool of one memory type, created now. Call it before the first
+// allocation from that pool.
+VMA_CALL_PRE VkResult VMA_CALL_POST vmaQtReserveBlocks(
+    VmaAllocator allocator,
+    uint32_t memoryTypeIndex,
+    size_t blockCount)
+{
+    VMA_ASSERT(allocator != VK_NULL_HANDLE);
+    if (memoryTypeIndex >= allocator->GetMemoryTypeCount() ||
+        allocator->m_pBlockVectors[memoryTypeIndex] == VMA_NULL)
+        return VK_ERROR_FEATURE_NOT_PRESENT;
+    return allocator->m_pBlockVectors[memoryTypeIndex]->QtReserveBlocks(blockCount);
+}
+
 VMA_CALL_PRE VkResult VMA_CALL_POST vmaFindMemoryTypeIndexForBufferInfo(
     VmaAllocator allocator,
     const VkBufferCreateInfo* pBufferCreateInfo,
