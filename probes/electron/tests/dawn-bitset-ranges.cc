// Copyright 2025 The Dawn & Tint Authors
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
// 1. Redistributions of source code must retain the above copyright notice, this
//    list of conditions and the following disclaimer.
//
// 2. Redistributions in binary form must reproduce the above copyright notice,
//    this list of conditions and the following disclaimer in the documentation
//    and/or other materials provided with the distribution.
//
// 3. Neither the name of the copyright holder nor the names of its
//    contributors may be used to endorse or promote products derived from
//    this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
// FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
// DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
// SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
// CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
// OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

// Adapted from Dawn BitSetRangeIteratorTests.cpp at 33259aa3b76e443342339dd78cf666f90692b9fd.
// The production header supplies the iterator. Expected ranges also define the input bits.
#include <bitset>
#include <cstdint>
#include <cstdio>
#include <initializer_list>
#include <vector>

#include "src/dawn/common/BitSetRangeIterator.h"

struct Range {
    uint32_t offset;
    size_t size;
};
enum class Index : uint32_t {};
static unsigned calls;

template <size_t N, typename T>
bool CheckTyped(const char* name, const std::vector<Range>& expected) {
    std::bitset<N> bits;
    for (const auto& range : expected) {
        if (range.offset > N || range.size > N - range.offset) {
            std::fprintf(stderr, "invalid input N=%zu %s\n", N, name);
            return false;
        }
        for (size_t i = 0; i < range.size; ++i) {
            bits.set(range.offset + i);
        }
    }
    dawn::BitSetRangeIterator<N, T> ranges(bits);
    auto it = ranges.begin();
    const auto end = ranges.end();
    for (const auto& want : expected) {
        if (it == end) {
            std::fprintf(stderr, "early end N=%zu %s\n", N, name);
            return false;
        }
        const auto [offset, size] = *it;
        if (static_cast<uint32_t>(offset) != want.offset || size != want.size) {
            std::fprintf(stderr, "range mismatch N=%zu %s\n", N, name);
            return false;
        }
        ++it;
    }
    if (!(it == end)) {
        std::fprintf(stderr, "extra range N=%zu %s\n", N, name);
        return false;
    }
    ++calls;
    return true;
}

template <size_t N>
bool Check(const char* name, const std::vector<Range>& expected) {
    return CheckTyped<N, uint32_t>(name, expected) && CheckTyped<N, Index>(name, expected);
}

template <size_t N>
bool Cases() {
    if (!Check<N>("empty", {})) return false;
    if constexpr (N == 0) {
        return Check<N>("full-zero-width", {});
    } else {
        if (!Check<N>("full", {{0, N}}) ||
            !Check<N>("high-bit", {{N - 1, 1}}) ||
            !Check<N>("low-bit", {{0, 1}})) return false;
        std::vector<Range> even;
        std::vector<Range> odd;
        for (uint32_t i = 0; i < N; ++i) {
            (i % 2 == 0 ? even : odd).push_back({i, 1});
        }
        if (!Check<N>("alternating-even", even) ||
            !Check<N>("alternating-odd", odd)) return false;
        if constexpr (N > 8) {
            if (!Check<N>("sparse", {{0, 1}, {3, 2}, {N - 1, 1}}) ||
                !Check<N>("high-run", {{N - 2, 2}})) return false;
        }
        if constexpr (N > 64) {
            if (!Check<N>("cross-word", {{62, N == 65 ? 3 : 5}}) ||
                !Check<N>("wide-tail", {{63, N - 63}})) return false;
        }
        return true;
    }
}

int main() {
    if (!Cases<0>() || !Cases<1>() || !Cases<63>() || !Cases<64>() ||
        !Cases<65>() || !Cases<127>() || !Cases<128>()) return 1;
    std::printf("PASS %u actual-header range calls\n", calls);
    return 0;
}
