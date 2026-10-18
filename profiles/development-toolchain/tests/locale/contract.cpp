// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Exercise actual libstdc++ locale conversions.
#include <atomic>
#include <cassert>
#include <cerrno>
#include <clocale>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <type_traits>

#ifdef NDEBUG
#error This contract requires enabled assertions
#endif

static std::__c_locale c_locale;

template<class T> static void numeric_contract()
{
    const char* valid[] = {"1.5", "+1.5", " 1.5", "-0", "0x1.8p+0", "1e-9999"};
    const T expected[] = {T(1.5), T(1.5), T(1.5), T(-0.0), T(1.5), T(0)};
    for (unsigned i = 0; i != 6; ++i) {
        T value = T(9);
        std::ios_base::iostate state = std::ios_base::goodbit;
        std::__convert_to_v(valid[i], value, state, c_locale);
        assert(state == std::ios_base::goodbit && value == expected[i]);
        if (i == 3)
            assert(std::signbit(value));
    }
    for (const char* input : {"", "text"}) {
        T value = T(9);
        std::ios_base::iostate state = std::ios_base::goodbit;
        std::__convert_to_v(input, value, state, c_locale);
        assert(state == std::ios_base::failbit && value == T(0));
    }
    for (const char* input : {"1.5tail", "1e"}) {
        T value = T(9);
        std::ios_base::iostate state = std::ios_base::goodbit;
        std::__convert_to_v(input, value, state, c_locale);
#if defined(__NetBSD__) && (!defined(_GLIBCXX_HAVE_STRTOLD) || defined(_GLIBCXX_HAVE_BROKEN_STRTOLD))
        if constexpr (std::is_same_v<T, long double>) {
            // Preserve the configured generic backend's sscanf fallback.
            assert(state == std::ios_base::goodbit && value == (input[1] == '.' ? T(1.5) : T(1)));
        } else
#endif
            assert(state == std::ios_base::failbit && value == T(0));
    }
    for (const char* input : {"1e9999", "-1e9999"}) {
        T value = T(0);
        std::ios_base::iostate state = std::ios_base::goodbit;
        std::__convert_to_v(input, value, state, c_locale);
        assert(state == std::ios_base::failbit);
        assert(value == (input[0] == '-' ? -std::numeric_limits<T>::max() : std::numeric_limits<T>::max()));
    }
    T value = T(0);
    errno = EDOM;
    std::ios_base::iostate state = std::ios_base::goodbit;
    std::__convert_to_v("1.5", value, state, c_locale);
    assert(value == T(1.5) && state == std::ios_base::goodbit && errno == EDOM);
}

static void conversions()
{
    char text[80];
    int length = std::__convert_from_v(c_locale, text, sizeof text, "%.2f", 1.5);
    assert(length == 4 && std::strcmp(text, "1.50") == 0);
    length = std::__convert_from_v(c_locale, text, sizeof text, "%.2Lf", 1.5L);
    assert(length == 4 && std::strcmp(text, "1.50") == 0);
    length = std::__convert_from_v(c_locale, text, 3, "%.2f", 1.5);
    assert(length == 4 && std::strcmp(text, "1.") == 0);
    numeric_contract<float>();
    numeric_contract<double>();
    numeric_contract<long double>();
}

static void public_stream_contract()
{
    for (const char* input : {"+1.5tail", " 1.5", "-0"}) {
        std::istringstream parser(input);
        parser.imbue(std::locale::classic());
        double value = 9;
        parser >> value;
        assert(!parser.fail());
        assert(value == (input[0] == '-' ? -0.0 : 1.5));
        if (input[0] == '-')
            assert(std::signbit(value));
    }
    for (const char* input : {"1e", "text", "1e9999", "inf", "nan"}) {
        std::istringstream parser(input);
        parser.imbue(std::locale::classic());
        double value = 9;
        parser >> value;
        assert(parser.fail());
    }
    for (double value : {0.1, -0.0, 1.5, std::numeric_limits<double>::min(),
                         std::numeric_limits<double>::max()}) {
        std::stringstream stream;
        stream.imbue(std::locale::classic());
        stream << std::setprecision(std::numeric_limits<double>::max_digits10) << value;
        double parsed = 9;
        stream >> parsed;
        assert(!stream.fail() && parsed == value && std::signbit(parsed) == std::signbit(value));
    }
#if defined(__NetBSD__)
    bool rejected = false;
    try { std::locale named("fr_FR.UTF-8"); }
    catch (const std::runtime_error&) { rejected = true; }
    assert(rejected); // Preserve the existing generic backend's named-locale boundary.
#endif
}

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::fputs("Usage: contract COMMA_LOCALE\n", stderr);
        return 2;
    }
    const char* selected = std::setlocale(LC_ALL, argv[1]);
    assert(selected);
    const char* decimal = std::localeconv()->decimal_point;
    assert(std::strcmp(decimal, ",") == 0);
    const std::string ambient = std::setlocale(LC_ALL, nullptr);
#if defined(__NetBSD__)
    c_locale = nullptr; // The existing generic ABI ignores this int* handle.
#else
    c_locale = newlocale(LC_ALL_MASK, "C", nullptr);
    assert(c_locale);
#endif
    conversions();
    public_stream_contract();
    std::fputs("PASS: serial numeric conversion and public stream semantics; starting workers.\n", stderr);
    std::atomic<unsigned> ready{0}, done{0};
    std::atomic<bool> start{false}, changed{false};
    auto worker = [&] {
        ready.fetch_add(1);
        while (!start.load())
            std::this_thread::yield();
        for (unsigned i = 0; i != 2000; ++i)
            conversions();
        done.fetch_add(1);
    };
    std::thread first(worker), second(worker);
    while (ready.load() != 2)
        std::this_thread::yield();
    start.store(true);
    while (done.load() != 2) {
        if (std::strcmp(std::localeconv()->decimal_point, ",") != 0)
            changed.store(true);
        std::this_thread::yield();
    }
    first.join();
    second.join();
    if (changed.load())
        std::fputs("FAIL: numeric conversion changed the process decimal locale\n", stderr);
    assert(!changed.load());
    const char* current = std::setlocale(LC_ALL, nullptr);
    assert(ambient == current);
#if !defined(__NetBSD__)
    freelocale(c_locale);
#endif
    std::puts("PASS: real float/double/long-double conversion, stream semantics, two workers, ambient locale.");
}
