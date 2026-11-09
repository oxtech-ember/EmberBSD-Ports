// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
// Compile the actual backend predicate with controlled frame and VMA state.
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>

constexpr int QVK_FRAMES_IN_FLIGHT = 2;
using quint64 = std::uint64_t;
using VkMemoryPropertyFlags = unsigned;
using VkResult = int;
using VkFence = int;
using VkDevice = void *;
constexpr VkResult VK_SUCCESS = 0;
constexpr VkResult VK_NOT_READY = 1;
static bool fenceSignaled[QVK_FRAMES_IN_FLIGHT];
static int fenceQueries = 0;
struct DeviceFunctions {
    VkResult vkGetFenceStatus(VkDevice, VkFence fence)
    {
        ++fenceQueries;
        return fenceSignaled[fence] ? VK_SUCCESS : VK_NOT_READY;
    }
};
constexpr unsigned VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT = 2;
static int optIn = 1;
static unsigned memoryFlags = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT;
static int allocationQueries = 0;
static int qEnvironmentVariableIntValue(const char *) { return optIn; }
static void *toVmaAllocator(void *p) { return p; }
static void *toVmaAllocation(void *p) { return p; }
static void vmaGetAllocationMemoryProperties(void *, void *, unsigned *out)
{
    ++allocationQueries;
    *out = memoryFlags;
}
struct QVkBuffer {
    std::uint64_t lastUsedOffscreenFrame = 0;
    void *allocations[1]{};
};
struct QVkSwapChain { bool cmdFenceWaitable[QVK_FRAMES_IN_FLIGHT]{}; };
struct SwapChains : std::vector<QVkSwapChain *> {
    bool isEmpty() const { return empty(); }
};
struct QRhiVulkan {
    int hostStaticUploads = -1;
    struct {
        bool active = true;
        bool cmdFenceWaitable[QVK_FRAMES_IN_FLIGHT]{};
        VkFence cmdFence[QVK_FRAMES_IN_FLIGHT]{0, 1};
    } ofr;
    DeviceFunctions functions;
    DeviceFunctions *df = &functions;
    VkDevice dev = nullptr;
    std::uint64_t offscreenFrameSerial = 1;
    bool offscreenFrameHasExternalCommands = false;
    int currentFrameSlot = 1;
    void *allocator = nullptr;
    SwapChains swapchains;
    bool canWriteStaticBufferDirectly(QVkBuffer *);
};

#include "predicate.inc"

static void require(bool condition, const char *name)
{
    if (!condition) {
        std::fprintf(stderr, "FAIL: %s\n", name);
        std::exit(1);
    }
}

int main()
{
    QRhiVulkan rhi;
    QVkBuffer buffer;
    require(rhi.canWriteStaticBufferDirectly(&buffer), "idle offscreen upload");
    QVkSwapChain swapchain;
    swapchain.cmdFenceWaitable[0] = true;
    rhi.swapchains.push_back(&swapchain);
    allocationQueries = 0;
    require(!rhi.canWriteStaticBufferDirectly(&buffer), "pending swapchain must use staging");
    require(allocationQueries == 0, "reject before accessing allocation");
    swapchain.cmdFenceWaitable[0] = false;
    require(!rhi.canWriteStaticBufferDirectly(&buffer), "registered swapchain uses staging");
    rhi.swapchains.clear();
    require(rhi.canWriteStaticBufferDirectly(&buffer), "offscreen upload after unregister");
    rhi.offscreenFrameHasExternalCommands = true;
    require(!rhi.canWriteStaticBufferDirectly(&buffer), "external reads must use staging");
    rhi.offscreenFrameHasExternalCommands = false;
    buffer.lastUsedOffscreenFrame = rhi.offscreenFrameSerial;
    require(!rhi.canWriteStaticBufferDirectly(&buffer), "buffer already used by this frame");
    ++rhi.offscreenFrameSerial;
    rhi.ofr.cmdFenceWaitable[0] = true;
    fenceQueries = 0;
    require(!rhi.canWriteStaticBufferDirectly(&buffer), "unfinished offscreen frame");
    require(!rhi.canWriteStaticBufferDirectly(&buffer), "still unfinished in the same frame");
    require(fenceQueries == 1, "one fence query per frame");
    // The previous frame is on screen: its fence signaled, nothing reads the buffer.
    ++rhi.offscreenFrameSerial;
    fenceSignaled[0] = true;
    fenceQueries = 0;
    require(rhi.canWriteStaticBufferDirectly(&buffer), "finished offscreen frame");
    require(rhi.canWriteStaticBufferDirectly(&buffer), "finished, same frame");
    require(fenceQueries == 1, "cached for the frame");
    fenceSignaled[0] = false;
    rhi.ofr.cmdFenceWaitable[0] = false;
    ++rhi.offscreenFrameSerial;
    memoryFlags = 0;
    require(!rhi.canWriteStaticBufferDirectly(&buffer), "device-only memory");
    memoryFlags = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT;
    rhi.ofr.active = false;
    require(!rhi.canWriteStaticBufferDirectly(&buffer), "outside offscreen frame");
    rhi.ofr.active = true;
    optIn = 0;
    rhi.hostStaticUploads = -1;
    require(!rhi.canWriteStaticBufferDirectly(&buffer), "default path unchanged");
    std::puts("PASS: actual host-upload predicate and staging fallbacks");
}
