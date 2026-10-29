// SPDX-License-Identifier: BSD-2-Clause
// Exercise Node's native module version check against the selected headers.
#include <node.h>

namespace {
void Initialize(v8::Local<v8::Object> exports) {
  (void)exports;
}
NODE_MODULE(ember_abi_fixture, Initialize)
}  // namespace
