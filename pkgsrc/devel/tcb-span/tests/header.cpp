// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <tcb/span.hpp>
int main() { int values[] = {7}; return tcb::span<int>(values)[0] == 7 ? 0 : 1; }
