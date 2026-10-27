/* SPDX-License-Identifier: BSD-2-Clause */
#include "boundary.h"
#include <cassert>
#include <cstdio>
#include <link.h>
#include <span>
#include <string_view>
#include <thread>

static bool cleaned;
static thread_local unsigned int local;
static void cleanup() { cleaned = true; }

static int loaded(struct dl_phdr_info *info, size_t, void *)
{
    if (info->dlpi_name && info->dlpi_name[0])
        std::printf("LOADED %s\n", info->dlpi_name);
    return 0;
}

int main()
{
    int values[] = {1, 2, 3};
    assert(std::span(values).size() == 3);
    assert(transform(std::string(128, 'x')) == std::string(128, 'x') + ":emberbsd");
    try {
        throw_across(cleanup);
        assert(false);
    } catch (const std::runtime_error &error) {
        assert(std::string_view(error.what()) == "unwind across DSO");
    }
    assert(cleaned);
    local = 17;
    std::thread thread([] { assert(local == 0); local = 19; });
    thread.join();
    assert(local == 17);
    dl_iterate_phdr(loaded, nullptr);
}
