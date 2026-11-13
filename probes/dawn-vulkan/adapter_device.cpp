// Dawn native: enumerate adapters and create a device (Vulkan backend).
#include <cstdio>
#include <cstdlib>
#include <dawn/native/DawnNative.h>
#include <webgpu/webgpu_cpp.h>

int main() {
  dawn::native::Instance instance;
  wgpu::RequestAdapterOptions opts = {};
  opts.backendType = wgpu::BackendType::Vulkan;
  auto adapters = instance.EnumerateAdapters(&opts);
  std::printf("adapters=%zu\n", adapters.size());
  if (adapters.empty()) {
    std::fprintf(stderr, "no Dawn Vulkan adapters\n");
    return 2;
  }
  for (size_t i = 0; i < adapters.size(); ++i) {
    wgpu::AdapterInfo info = {};
    adapters[i].GetInfo(&info);
    std::printf("adapter[%zu] device=%s vendor=%s backend=%u\n", i,
                info.device ? info.device : "?",
                info.vendor ? info.vendor : "?",
                static_cast<unsigned>(info.backendType));
  }
  wgpu::DeviceDescriptor desc = {};
  wgpu::Device device = adapters[0].CreateDevice(&desc);
  if (!device) {
    std::fprintf(stderr, "CreateDevice failed\n");
    return 3;
  }
  std::puts("PASS");
  return 0;
}
