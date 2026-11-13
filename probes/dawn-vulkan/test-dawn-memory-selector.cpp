// SPDX-License-Identifier: MIT
// Origin: EmberBSD contributors (AI-assisted).
#include "src/dawn/native/vulkan/MemoryTypeSelector.h"
#include <cassert>
#include <cstdio>
using namespace dawn::native::vulkan;
int main() {
 const auto d=VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, v=VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT;
 const auto c=VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, h=VK_MEMORY_PROPERTY_HOST_CACHED_BIT;
 std::vector<VkMemoryHeap> heaps(2); heaps[0].size=100; heaps[1].size=1000;
 std::vector<VkMemoryType> types={{d,1},{v|h,0},{v|c,0},{d|v|c,1},{v|c|h,0}};
 MemoryTypeSelector normal(types,heaps), avoid(types,heaps,true);
 VkMemoryRequirements req{}; req.memoryTypeBits=(1<<2)|(1<<3);
 assert(normal.FindBestTypeIndex(req,MemoryKind::WriteMappable)==3);
 assert(avoid.FindBestTypeIndex(req,MemoryKind::WriteMappable)==2);
 req.memoryTypeBits=1; assert(avoid.FindBestTypeIndex(req,MemoryKind::DeviceLocal)==0);
 req.memoryTypeBits=1<<3; assert(avoid.FindBestTypeIndex(req,MemoryKind::WriteMappable)==kInvalidMemoryTypeIndex);
 req.memoryTypeBits=31; assert(avoid.FindBestTypeIndex(req,static_cast<MemoryKind>(20))==kInvalidMemoryTypeIndex);
 req.memoryTypeBits=(1<<1)|(1<<2); assert(avoid.FindBestTypeIndex(req,MemoryKind::ReadMappable)==1); assert(avoid.FindBestTypeIndex(req,MemoryKind::WriteMappable)==2);
 req.memoryTypeBits=(1<<2)|(1<<4); assert(avoid.FindBestTypeIndex(req,MemoryKind::ReadMappable)==4);
 // Captured Raven2 memory properties; retain original type indices and mask.
 std::vector<VkMemoryHeap> nickHeaps(2);
 nickHeaps[0].size=1163218944; nickHeaps[1].size=2326441984;
 std::vector<VkMemoryType> nickTypes={{0x01,1},{0x01,1},{0x06,0},{0x07,1},{0x07,1},
                                      {0x0e,0},{0x0e,0},{0xc1,1},{0xc6,0},{0xc7,1},{0xce,0}};
 MemoryTypeSelector nickDefault(nickTypes,nickHeaps), nickAvoid(nickTypes,nickHeaps,true);
 req.memoryTypeBits=0x7ad;
 assert(nickDefault.FindBestTypeIndex(req,MemoryKind::ReadMappable)==5);
 assert(nickAvoid.FindBestTypeIndex(req,MemoryKind::ReadMappable)==5);
 assert(nickDefault.FindBestTypeIndex(req,MemoryKind::WriteMappable)==3);
 assert(nickAvoid.FindBestTypeIndex(req,MemoryKind::WriteMappable)==2);
 assert(nickAvoid.FindBestTypeIndex(req,MemoryKind::DeviceLocal)==0);
 puts("Dawn memory selector regression PASS");
}
