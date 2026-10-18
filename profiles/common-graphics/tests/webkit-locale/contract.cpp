// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Exercise real Skia locale scopes and string APIs.
#include "include/core/SkString.h"
#include "include/utils/SkParse.h"
#include "src/core/SkAutoLocaleSetter.h"
#include "src/sksl/SkSLString.h"

#include <atomic>
#include <cassert>
#include <clocale>
#include <cstdio>
#include <cstring>
#include <string>
#include <thread>

#ifdef NDEBUG
#error This contract requires enabled assertions
#endif

static void check(const char* expected, const char* number)
{
    SkString text;
    text.printf("%.2f", 1.5);
    if (std::strcmp(text.c_str(), expected) != 0)
        std::fprintf(stderr, "SkString expected [%s], obtained [%s]\n", expected, text.c_str());
    assert(std::strcmp(text.c_str(), expected) == 0);
    assert(SkSL::String::printf("%.2f", 1.5) == expected);

    const std::string padding(1200, 'x');
    const std::string complete = padding + expected;
    text.printf("%s%.2f", padding.c_str(), 1.5);
    assert(std::strcmp(text.c_str(), complete.c_str()) == 0);
    assert(SkSL::String::printf("%s%.2f", padding.c_str(), 1.5) == complete);

    float value = 0;
    const char* end = SkParse::FindScalar(number, &value);
    assert(end && *end == '\0' && value == 1.5f);
    assert(skstd::to_string(1.5) == "1.5");
    float parsed = 0;
    assert(SkSL::stod("1.5", &parsed) && parsed == 1.5f);
}

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::fputs("Usage: contract COMMA_LOCALE\n", stderr);
        return 2;
    }
    // Change the process locale before creating workers. The test never mutates
    // it concurrently. Each nested scope must preserve that ambient locale.
    const char* selected = std::setlocale(LC_ALL, argv[1]);
    assert(selected);
    const char* decimal = std::localeconv()->decimal_point;
    assert(std::strcmp(decimal, ",") == 0);
    const std::string ambient = std::setlocale(LC_ALL, nullptr);
    check("1,50", "1,5");
    {
        SkAutoLocaleSetter outer("C");
        check("1.50", "1.5");
        {
            SkAutoLocaleSetter inner(argv[1]);
            check("1,50", "1,5");
        }
        check("1.50", "1.5");
    }
    check("1,50", "1,5");

    std::atomic<unsigned> ready{0};
    auto worker = [&](bool useC) {
        SkAutoLocaleSetter locale(useC ? "C" : argv[1]);
        ready.fetch_add(1);
        while (ready.load() != 2)
            std::this_thread::yield();
        for (unsigned i = 0; i != 200; ++i) {
            check(useC ? "1.50" : "1,50", useC ? "1.5" : "1,5");
            {
                SkAutoLocaleSetter nested(useC ? argv[1] : "C");
                check(useC ? "1,50" : "1.50", useC ? "1,5" : "1.5");
            }
            check(useC ? "1.50" : "1,50", useC ? "1.5" : "1,5");
        }
    };
    std::thread first(worker, true);
    std::thread second(worker, false);
    first.join();
    second.join();
    check("1,50", "1,5");
    const char* current = std::setlocale(LC_ALL, nullptr);
    assert(ambient == current);
    std::puts("PASS: real Skia formatting/parsing, nested scopes, two workers, ambient locale.");
}
