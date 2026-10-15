// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD; AI-assisted generic-sized atomic runtime contract.
#include <atomic>
#include <cstdio>
#include <thread>
struct Block { int value[64]; };
static_assert(sizeof(Block) == 256);
int main() {
    std::atomic<Block> state(Block{});
    if (state.is_lock_free()) return 1;
    Block ones{};
    for (int& item : ones.value) item = 1;
    state.store(ones);
    Block old = state.exchange(Block{});
    for (int item : old.value) if (item != 1) return 2;
    auto increment = [&state]() {
        for (int step = 0; step < 1000; ++step) {
            Block expected = state.load();
            Block desired{};
            do {
                for (int i = 0; i < 64; ++i) desired.value[i] = expected.value[i] + 1;
            } while (!state.compare_exchange_weak(expected, desired));
        }
    };
    std::thread first(increment), second(increment);
    first.join(); second.join();
    const Block result = state.load();
    for (int item : result.value) if (item != 2000) return 3;
    std::puts("PASS GCC16 libatomic: 256-byte store/load/exchange/CAS, 2000 thread updates");
}
