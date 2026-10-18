// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Native runtime contract, not LLVM metadata.
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

int main()
{
    const std::vector<int> values{1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    int sum = 0;
    std::thread worker([&] { sum = std::accumulate(values.begin(), values.end(), 0); });
    worker.join();
    if (sum != 55)
        return 1;
    try {
        throw std::runtime_error("GCC16 native exception");
    } catch (const std::exception& error) {
        if (std::string(error.what()) != "GCC16 native exception")
            return 2;
    }
    std::cout << "PASS: native threads, containers, exceptions and I/O\n";
    return 0;
}
