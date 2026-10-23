// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted E12 GCC16 regression).
#include <functional>
#include <utility>

struct StopArgs {
  std::function<void()> async_stop_closure;

  std::function<void()> HandleStopAsynchronously() const {
    return async_stop_closure;
  }
};

void track_event_stop_clone_control(const StopArgs& args) {
  auto outer_stop_closure = args.HandleStopAsynchronously();
  StopArgs inner_stop_args{};
  inner_stop_args.async_stop_closure = [outer_stop_closure] {
    outer_stop_closure();
  };

  // std::function copy clones this closure. Copying the captured function
  // reaches the same virtual clone path during that operation.
  std::function<void()> copied_stop_closure = inner_stop_args.async_stop_closure;
  if (copied_stop_closure)
    std::move(copied_stop_closure)();
}
