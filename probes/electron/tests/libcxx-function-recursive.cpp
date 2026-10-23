// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted E12 regression control).
#include <functional>
#include <new>

int recursive_function_control(int depth) {
  std::function<int(int)> callback;
  callback = [&callback](int value) {
    return value <= 0 ? 0 : callback(value - 1) + 1;
  };
  return callback(depth);
}
