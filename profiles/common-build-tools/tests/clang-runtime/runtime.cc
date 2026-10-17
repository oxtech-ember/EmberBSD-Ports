// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), selected native GCC16 C++ ABI/runtime.
#include <atomic>
#include <numeric>
#include <stdexcept>
#include <thread>
#include <vector>

int main()
{
    std::vector<int> values{10, 12, 20};
    std::atomic<int> result{0};
    std::thread worker([&] { result = std::accumulate(values.begin(), values.end(), 0); });
    worker.join();
    try {
        if (result != 42)
            return 1;
        throw std::runtime_error("Ember Clang exception");
    } catch (const std::runtime_error &error) {
        return std::string(error.what()) == "Ember Clang exception" ? 0 : 2;
    }
}
