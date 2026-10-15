/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors (AI-assisted).
 * Allocate and throw inside the DSO; the executable owns returned objects.
 */
#include "cxx-runtime.hpp"

#include <stdexcept>

namespace e35 {
unsigned int
compiler_major() noexcept
{
	return __GNUC__;
}

std::string
make_text()
{
	return std::string(4096, 'q') + "E35";
}

[[noreturn]] void
throw_error()
{
	throw std::runtime_error("E35 cross-DSO runtime_error");
}

unsigned int
next_tls() noexcept
{
	static thread_local unsigned int counter;

	return ++counter;
}
}
