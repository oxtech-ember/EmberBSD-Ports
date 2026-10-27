/* SPDX-License-Identifier: BSD-2-Clause */
#include "boundary.h"

std::string transform(const std::string &input)
{
    return input + ":emberbsd";
}

void throw_across(void (*cleanup)())
{
    struct Guard {
        void (*cleanup)();
        ~Guard() { cleanup(); }
    } guard{cleanup};
    throw std::runtime_error("unwind across DSO");
}
