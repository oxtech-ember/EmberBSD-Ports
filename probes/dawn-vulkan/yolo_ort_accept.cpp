// Acceptance: YOLO26n ONNX Runtime WebGPU vs CPU inferenceMs on Nick.
#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <onnxruntime_cxx_api.h>

static double runOnce(Ort::Session &session, const char *inName, const char *outName,
                      std::vector<float> &input)
{
  const std::array<int64_t, 4> shape{1, 3, 480, 640};
  auto memory = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
  Ort::Value tensor = Ort::Value::CreateTensor<float>(
      memory, input.data(), input.size(), shape.data(), shape.size());
  const char *inputs[] = {inName};
  const char *outputs[] = {outName};
  auto t0 = std::chrono::steady_clock::now();
  auto out = session.Run(Ort::RunOptions{nullptr}, inputs, &tensor, 1, outputs, 1);
  auto t1 = std::chrono::steady_clock::now();
  (void)out;
  return std::chrono::duration<double, std::milli>(t1 - t0).count();
}

static Ort::Session makeSession(Ort::Env &env, const char *model, bool webgpu)
{
  Ort::SessionOptions options;
  options.SetIntraOpNumThreads(2);
  options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
  if (webgpu) {
    if (!std::getenv("ORT_WEBGPU_EP_ALLOW_SOFTWARE_ADAPTER"))
      setenv("ORT_WEBGPU_EP_ALLOW_SOFTWARE_ADAPTER", "1", 0);
    const char *plugin = std::getenv("ORT_WEBGPU_LIBRARY");
    const std::string path = plugin && *plugin ? plugin
                                               : "/usr/pkg/lib/libonnxruntime_providers_webgpu.so";
    env.RegisterExecutionProviderLibrary("accept_webgpu", path);
    bool appended = false;
    for (const auto &device : env.GetEpDevices()) {
      const char *name = device.EpName();
      // Upstream name: "WebGpuExecutionProvider"
      if (!name || (!std::strstr(name, "WebGpu") && !std::strstr(name, "WebGPU")))
        continue;
      options.AppendExecutionProvider_V2(env, {device}, {});
      appended = true;
      break;
    }
    if (!appended)
      throw Ort::Exception("WebGpuExecutionProvider not advertised by plugin", ORT_FAIL);
  }
  return Ort::Session(env, model, options);
}

int main(int argc, char **argv)
{
  const char *model = argc > 1 ? argv[1] : "/usr/pkg/share/plutosky/YOLO26n640x480.onnx";
  Ort::Env env{ORT_LOGGING_LEVEL_WARNING, "yolo-accept"};
  std::vector<float> input(1 * 3 * 480 * 640, 0.5f);
  try {
    auto cpu = makeSession(env, model, false);
    Ort::AllocatorWithDefaultOptions alloc;
    auto inName = cpu.GetInputNameAllocated(0, alloc);
    auto outName = cpu.GetOutputNameAllocated(0, alloc);
    double cpuMs = 0;
    for (int i = 0; i < 3; ++i)
      cpuMs += runOnce(cpu, inName.get(), outName.get(), input);
    cpuMs /= 3;
    std::printf("CPU inferenceMs=%.1f\n", cpuMs);

    double gpuMs = -1;
    try {
      auto gpu = makeSession(env, model, true);
      gpuMs = 0;
      for (int i = 0; i < 3; ++i)
        gpuMs += runOnce(gpu, inName.get(), outName.get(), input);
      gpuMs /= 3;
      std::printf("WebGPU inferenceMs=%.1f\n", gpuMs);
    } catch (const Ort::Exception &e) {
      std::printf("WebGPU unavailable: %s\n", e.what());
    }
    return 0;
  } catch (const Ort::Exception &e) {
    std::fprintf(stderr, "FAIL: %s\n", e.what());
    return 1;
  }
}
