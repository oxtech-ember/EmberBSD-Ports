// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors
// Derived from the gzip-hpp 0.1.0 API and KiCad 10.0.8 gzip-hpp patch.

#include <gzip/decompress.hpp>

#include <cassert>
#include <stdexcept>
#include <string>

int main()
{
    static_assert(gzip::detail::default_max_uncompressed_size == 1000000000,
                  "value-returning decompression retains the 1 GB safety cap");

    constexpr char compressed[] = {
        '\x1f', '\x8b', '\x08', '\x00', '\x00', '\x00', '\x00', '\x00',
        '\x00', '\xff', '\xcb', '\x48', '\xcd', '\xc9', '\xc9', '\x57',
        '\x48', '\xaf', '\xca', '\x2c', '\xd0', '\xcd', '\x28', '\x28',
        '\x00', '\x00', '\x96', '\x04', '\xd1', '\x87', '\x0e', '\x00',
        '\x00', '\x00',
    };
    constexpr std::size_t compressed_size = sizeof(compressed);
    const std::string expected = "hello gzip-hpp";

    const std::string input(compressed, compressed_size);
    assert(gzip::decompress(compressed, compressed_size) == expected);
    assert(gzip::decompress(input) == expected);
    assert(gzip::decompress(compressed, compressed_size, 0) == expected);
    assert(gzip::decompress(input, 0) == expected);

    std::string unlimited;
    gzip::decompress(compressed, compressed_size, unlimited, 0, 4);
    assert(unlimited == expected);

    bool rejected = false;
    try
    {
        std::string bounded;
        gzip::decompress(compressed, compressed_size, bounded, expected.size() - 1, 4);
    }
    catch (const std::runtime_error&)
    {
        rejected = true;
    }
    assert(rejected);
}
