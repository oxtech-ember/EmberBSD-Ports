// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
// Build as a DSO with EMBER_RUNTIME_DSO, or as the static/dynamic caller.
#include <atomic>
#include <filesystem>
#include <iostream>
#include <locale>
#include <stdexcept>
#include <thread>

#ifdef EMBER_RUNTIME_DSO
extern "C" void ember_runtime_throw()
{
    throw std::runtime_error("runtime ABI");
}
#else
#ifdef EMBER_RUNTIME_SHARED_CALLER
extern "C" void ember_runtime_throw();
#else
static void ember_runtime_throw()
{
    throw std::runtime_error("runtime ABI");
}
#endif

static int initialized;
struct initialize {
    initialize() { initialized = 17; }
};
static initialize initial;
static thread_local int local = 3;

int main()
{
    std::atomic<int> result{0};
    std::thread worker([&result] {
        local = 5;
        result.store(local);
    });
    worker.join();
    if (result.load() != 5 || local != 3 || initialized != 17)
        return 1;
    const auto path = std::filesystem::path("one") / "two";
    if (path.generic_string() != "one/two" || std::locale::classic().name() != "C")
        return 2;
    try {
        ember_runtime_throw();
        return 3;
    } catch (const std::runtime_error& error) {
        if (std::string(error.what()) != "runtime ABI")
            return 4;
    }
    std::cout << "PASS: C++ constructors, TLS, threads, locale, filesystem and exceptions\n";
}
#endif
