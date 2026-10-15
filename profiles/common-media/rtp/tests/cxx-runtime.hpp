/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors (AI-assisted).
 */
#ifndef E35_CXX_RUNTIME_HPP
#define E35_CXX_RUNTIME_HPP

#include <string>

namespace e35 {
unsigned int compiler_major() noexcept;
std::string make_text();
[[noreturn]] void throw_error();
unsigned int next_tls() noexcept;
}

#endif
