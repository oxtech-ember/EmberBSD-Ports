// SPDX-License-Identifier: ISC
// Exercise the installed context ABI, including resuming a suspended stack.
#include <libcontext.h>

#include <array>
#include <cstdio>
#include <cstdlib>

namespace {
alignas(16) std::array<unsigned char, 64 * 1024> stack;
libcontext::fcontext_t caller;
libcontext::fcontext_t worker;
int phase;

void enter(intptr_t value)
{
    if (value != 41)
        std::abort();
    phase = 1;
    value = libcontext::jump_fcontext(&worker, caller, 42);
    if (value != 73)
        std::abort();
    phase = 2;
    libcontext::jump_fcontext(&worker, caller, 74);
    std::abort();
}
}

int main()
{
    worker = libcontext::make_fcontext(stack.data() + stack.size(), stack.size(), enter);
    if (!worker)
        return 1;
    if (libcontext::jump_fcontext(&caller, worker, 41) != 42 || phase != 1)
        return 2;
    if (libcontext::jump_fcontext(&caller, worker, 73) != 74 || phase != 2)
        return 3;
    libcontext::release_fcontext(worker);
    std::puts("libcontext: two context transfers and stack resumption passed");
}
