// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <spdlog/spdlog.h>
int main() { spdlog::set_level(spdlog::level::off); spdlog::info("{}", 42); return 0; }
