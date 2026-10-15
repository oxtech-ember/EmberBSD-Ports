// SPDX-License-Identifier: MIT
#include <onnxruntime_cxx_api.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "onnx-graph.h"

static void require(bool ok, const char *what) {
    if (!ok) throw std::runtime_error(what);
}
int main() try {
    require(std::string(OrtGetApiBase()->GetVersionString()) == "1.31.0", "unexpected ONNX Runtime version");
    const auto providers = Ort::GetAvailableProviders();
    require(providers.size() == 1 && providers[0] == "CPUExecutionProvider", "expected only CPU provider");
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "ember-onnx");
    Ort::SessionOptions options;
    options.SetIntraOpNumThreads(1).SetInterOpNumThreads(1);
    options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
    const auto model = graph();
    Ort::Session session(env, model.data(), model.size(), options);
    auto memory = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
    std::array<float, 6> data{-4, -2, -1, 0, 1, 10};
    std::array<int64_t, 1> shape{6};
    auto tensor = Ort::Value::CreateTensor<float>(memory, data.data(), data.size(), shape.data(), shape.size());
    const char *inputs[] = {"x"}, *outputs[] = {"y"};
    const std::array<float, 6> expected{0, 0, 1, 2, 3, 12};
    for (int run = 0; run < 100; ++run) {
        auto results = session.Run(Ort::RunOptions{nullptr}, inputs, &tensor, 1, outputs, 1);
        require(results.size() == 1 && results[0].IsTensor(), "missing result tensor");
        require(results[0].GetTensorTypeAndShapeInfo().GetShape() == std::vector<int64_t>{6}, "wrong result shape");
        auto values = results[0].GetTensorData<float>();
        for (size_t i = 0; i < expected.size(); ++i)
            require(std::isfinite(values[i]) && std::abs(values[i] - expected[i]) < 1e-6f, "wrong graph result");
    }
    bool rejected = false;
    try {
        const Bytes invalid = "not an ONNX model";
        Ort::Session bad(env, invalid.data(), invalid.size(), options);
    } catch (const Ort::Exception &) { rejected = true; }
    require(rejected, "invalid model accepted");
    rejected = false;
    try {
        std::array<int64_t, 1> bad_shape{3};
        auto bad = Ort::Value::CreateTensor<float>(memory, data.data(), 3, bad_shape.data(), 1);
        session.Run(Ort::RunOptions{nullptr}, inputs, &bad, 1, outputs, 1);
    } catch (const Ort::Exception &) { rejected = true; }
    require(rejected, "invalid input shape accepted");
    rejected = false;
    try {
        const char *bad_names[] = {"missing"};
        session.Run(Ort::RunOptions{nullptr}, bad_names, &tensor, 1, outputs, 1);
    } catch (const Ort::Exception &) { rejected = true; }
    require(rejected, "unknown input name accepted");
    std::cout << "PASS ONNX Runtime 1.31.0 CPU: Add/Relu, 100 runs, malformed model, shape and name rejection\n";
    return 0;
} catch (const std::exception &error) { std::cerr << error.what() << '\n'; return 1; }
