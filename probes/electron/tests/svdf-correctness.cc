// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
// Exercise the real hybrid SVDF and tensor-utils implementations.
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>

#include "tensorflow/lite/kernels/internal/reference/svdf.h"

namespace {
int failures = 0;

template <typename T, size_t N>
struct Guarded {
  T left = T(83);
  std::array<T, N> values{};
  T right = T(-83);

  void Check(const char* name) const {
    if (left != T(83) || right != T(-83)) {
      std::fprintf(stderr, "%s: guard changed\n", name);
      ++failures;
    }
  }
};

void CheckValue(const char* name, int index, float actual, float expected) {
  if (!std::isfinite(actual) || !std::isfinite(expected) ||
      std::fabs(actual - expected) > 0.0001f) {
    std::fprintf(stderr, "%s[%d]: got %.9g, expected %.9g\n", name, index,
                 actual, expected);
    ++failures;
  }
}

void RunScenario(bool asymmetric, bool relu) {
  constexpr std::array<int8_t, 8> weights = {1, 2, -1, 1, 2, -1, -2, -1};
  constexpr std::array<float, 12> time_weights = {1, 2, 3, 1, 2, 3,
                                                1, 2, 3, 1, 2, 3};
  constexpr std::array<float, 2> bias = {2, -3};
  constexpr std::array<float, 4> symmetric_input = {127, -127, -127, 127};
  constexpr std::array<float, 4> asymmetric_input = {0, 255, 255, 0};
  constexpr std::array<float, 4> zeros = {0, 0, 0, 0};
  // Independent exact products: (real input . integer feature row) * 0.5.
  // These inputs are represented exactly by both quantization modes.
  constexpr std::array<float, 8> symmetric_features = {
      -63.5, -127, 190.5, -63.5, 63.5, 127, -190.5, 63.5};
  constexpr std::array<float, 8> asymmetric_features = {
      255, 127.5, -127.5, -127.5, 127.5, -127.5, 255, -255};
  // Temporal coefficients are 3, 2 and 4 for the sequence input, zero, input.
  // Rank two sums adjacent filters. Only these None cases include the bias.
  constexpr float symmetric_output[3][4] = {
      {-569.5, 378, 573.5, -384},
      {-379, 251, 383, -257},
      {-760, 505, 764, -511}};
  constexpr float asymmetric_output[3][4] = {
      {1149.5, -768, 2, -3}, {767, -513, 2, -3}, {1532, -1023, 2, -3}};
  constexpr float symmetric_relu[4] = {0, 6, 6, 0};
  constexpr float asymmetric_relu[4] = {6, 0, 0, 0};
  constexpr int expected_row_sums[4] = {3, 0, 1, -3};
  constexpr int symmetric_quantized[4] = {127, -127, -127, 127};
  constexpr int asymmetric_quantized[4] = {-128, 127, 127, -128};
  const auto& features = asymmetric ? asymmetric_features : symmetric_features;
  const auto& input = asymmetric ? asymmetric_input : symmetric_input;
  Guarded<float, 8> scratch;
  Guarded<float, 2> scales;
  Guarded<int8_t, 4> quantized;
  Guarded<float, 24> state;
  Guarded<float, 4> output;
  Guarded<int32_t, 2> zero_points;
  Guarded<int32_t, 4> row_sums;
  bool compute_row_sums = true;
  TfLiteSVDFParams params{};
  params.rank = 2;
  params.activation = relu ? kTfLiteActRelu6 : kTfLiteActNone;
  params.asymmetric_quantize_inputs = asymmetric;
  const tflite::RuntimeShape input_shape({2, 2});
  const tflite::RuntimeShape feature_shape({4, 2});
  const tflite::RuntimeShape time_shape({4, 3});
  const tflite::RuntimeShape bias_shape({2});
  const tflite::RuntimeShape output_shape({2, 2});

  for (int step = 0; step < 3; ++step) {
    tflite::reference_ops::EvalHybridSVDF(
        &params, input_shape, (step == 1 ? zeros : input).data(),
        feature_shape, weights.data(), 0.5f, time_shape, time_weights.data(),
        bias_shape, relu ? nullptr : bias.data(), scratch.values.data(),
        scales.values.data(), quantized.values.data(), state.values.data(),
        output_shape, output.values.data(), zero_points.values.data(),
        row_sums.values.data(), &compute_row_sums);
    for (int i = 0; i < 4; ++i) {
      const float expected = relu ? (asymmetric ? asymmetric_relu[i]
                                               : symmetric_relu[i])
                                  : (asymmetric ? asymmetric_output[step][i]
                                                : symmetric_output[step][i]);
      CheckValue("output", i, output.values[i], expected);
      CheckValue("row sums", i, float(row_sums.values[i]),
                  float(expected_row_sums[i]));
      const int expected_q = asymmetric ? asymmetric_quantized[i]
                                       : symmetric_quantized[i];
      CheckValue("quantized", i, float(quantized.values[i]), float(expected_q));
    }
    const int coefficient = step == 0 ? 3 : (step == 1 ? 2 : 4);
    for (int i = 0; i < 8; ++i) {
      CheckValue("scratch", i, scratch.values[i], coefficient * features[i]);
      for (int j = 0; j < 3; ++j) {
        const bool has_feature = step == 0 ? j == 2
                                          : (step == 1 ? j == 1 : j != 1);
        CheckValue("state", i * 3 + j, state.values[i * 3 + j],
                    has_feature ? features[i] : 0);
      }
    }
    for (int i = 0; i < 2; ++i) {
      CheckValue("scale", i, scales.values[i], 0.5f);
      CheckValue("zero point", i, float(zero_points.values[i]),
                  asymmetric ? -128.0f : 0.0f);
    }
    if (compute_row_sums) {
      std::fprintf(stderr, "row-sum cache was not populated\n");
      ++failures;
    }
    scratch.Check("scratch");
    scales.Check("scales");
    quantized.Check("quantized");
    state.Check("state");
    output.Check("output");
    zero_points.Check("zero points");
    row_sums.Check("row sums");
  }
}
}  // namespace

int main() {
  for (bool asymmetric : {false, true}) {
    for (bool relu : {false, true}) {
      RunScenario(asymmetric, relu);
    }
  }
  if (failures) {
    std::fprintf(stderr, "FAIL: %d numerical or guard checks\n", failures);
    return 1;
  }
  std::puts("PASS: real EvalHybridSVDF, 12 calls, symmetric/asymmetric, "
            "rank 2, two batches, state history, bias, Relu6 and guards");
  return 0;
}
