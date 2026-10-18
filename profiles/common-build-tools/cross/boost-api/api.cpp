/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted), installed Boost API acceptance.
 */
#define BOOST_TEST_MODULE EmberBSDInstalledBoost
#ifdef EMBER_BOOST_NATIVE_HEADERS
#include <boost/test/included/unit_test.hpp>
#else
#define BOOST_TEST_DYN_LINK 1
#include <boost/test/unit_test.hpp>
#endif
#include <boost/locale/encoding_utf.hpp>
#include <boost/system/error_code.hpp>
#include <boost/version.hpp>
#include <cerrno>
#include <cstdlib>
#include <cstdint>
#include <string>

#ifndef EMBER_BOOST_NATIVE_HEADERS
#include <boost/filesystem.hpp>
#include <boost/locale.hpp>
#include <boost/thread.hpp>
#include <boost/thread/scoped_thread.hpp>
#include <algorithm>
#include <fstream>
#include <iomanip>
#include <iterator>
#include <sstream>
#include "loaded.h"

struct LibraryInventory {
    LibraryInventory()
    {
        const auto& suite = boost::unit_test::framework::master_test_suite();
        check_loaded(suite.argv[0]);
    }
};
BOOST_GLOBAL_FIXTURE(LibraryInventory);
#endif

BOOST_AUTO_TEST_CASE(system_error_contract)
{
    BOOST_TEST(BOOST_VERSION == 109200);
    const auto code = boost::system::errc::make_error_code(
        boost::system::errc::permission_denied);
    BOOST_TEST(code.value() == EACCES);
    BOOST_TEST(code == boost::system::errc::permission_denied);
    BOOST_TEST(code.category().name() == std::string("generic"));
    BOOST_TEST(!code.message().empty());
    if (std::getenv("EMBER_BOOST_FORCE_FAILURE") != nullptr)
        BOOST_FAIL("intentional Boost.Test failure control");
}

BOOST_AUTO_TEST_CASE(utf_conversion_contract)
{
    using namespace boost::locale::conv;
    const std::string text = "Привет, EmberBSD!";
    const auto decoded = utf_to_utf<char32_t>(text, stop);
    BOOST_CHECK(decoded == std::u32string(U"Привет, EmberBSD!"));
    BOOST_TEST(utf_to_utf<char>(decoded, stop) == text);
    const std::string invalid("\xc3\x28", 2);
    BOOST_CHECK_THROW(utf_to_utf<char32_t>(invalid, stop), conversion_error);
}

#ifndef EMBER_BOOST_NATIVE_HEADERS
BOOST_AUTO_TEST_CASE(filesystem_contract)
{
    namespace fs = boost::filesystem;
    struct Directory {
        fs::path path;
        ~Directory()
        {
            boost::system::error_code ignored;
            fs::remove_all(path, ignored);
        }
    };
    Directory temp{fs::temp_directory_path() / fs::unique_path("ember-boost-%%%%-%%%%-%%%%")};
    BOOST_REQUIRE(fs::create_directories(temp.path / "nested"));
    const auto input = temp.path / "nested/values.txt";
    const std::string expected = "EmberBSD Boost 42\n";
    {
        std::ofstream stream(input.string(), std::ios::binary);
        BOOST_REQUIRE(stream.good());
        stream << expected;
        stream.close();
        BOOST_REQUIRE(stream.good());
    }
    const auto copy = temp.path / "copy.txt";
    BOOST_REQUIRE(fs::copy_file(input, copy));
    BOOST_TEST(fs::file_size(copy) == expected.size());
    std::ifstream stream(copy.string(), std::ios::binary);
    const std::string actual((std::istreambuf_iterator<char>(stream)), {});
    BOOST_TEST(actual == expected);
    stream.close();
    boost::system::error_code error;
    BOOST_TEST(!fs::copy_file(input, copy, fs::copy_options::none, error));
    BOOST_TEST(error == boost::system::errc::file_exists);
    BOOST_TEST(!fs::copy_file(temp.path / "missing", temp.path / "missing-copy", fs::copy_options::none, error));
    BOOST_TEST(error == boost::system::errc::no_such_file_or_directory);
    fs::rename(copy, temp.path / "renamed.txt");
    BOOST_TEST(fs::canonical(temp.path / "nested/../renamed.txt") == fs::canonical(temp.path / "renamed.txt"));
    BOOST_TEST(fs::remove_all(temp.path) == 4U);
}

BOOST_AUTO_TEST_CASE(thread_future_contract)
{
    for (unsigned iteration = 0; iteration < 4; ++iteration) {
        boost::promise<std::uint64_t> promise;
        auto result = promise.get_future();
        boost::scoped_thread<> worker{boost::thread([&promise] {
            std::uint64_t sum = 0;
            for (unsigned value = 1; value <= 1000; ++value)
                sum += value;
            promise.set_value(sum);
        })};
        BOOST_TEST(result.get() == 500500U);
    }
}

BOOST_AUTO_TEST_CASE(icu_locale_contract)
{
    auto manager = boost::locale::localization_backend_manager::global();
    const auto backends = manager.get_all_backends();
    BOOST_REQUIRE(std::find(backends.begin(), backends.end(), "icu") != backends.end());
    manager.select("icu");
    boost::locale::generator generator(manager);
    generator.locale_cache_enabled(false);
    const auto locale = generator("en_US.UTF-8");
    BOOST_TEST(boost::locale::to_upper("Привет, EmberBSD!", locale) == "ПРИВЕТ, EMBERBSD!");
    const std::string decomposed("e\xcc\x81", 3);
    BOOST_TEST(boost::locale::normalize("é", boost::locale::norm_nfd, locale) == decomposed);
    BOOST_TEST(boost::locale::normalize(decomposed, boost::locale::norm_nfc, locale) == "é");
    const std::string cp1251("\xcf\xf0\xe8\xe2\xe5\xf2", 6);
    BOOST_TEST(boost::locale::conv::between(cp1251, "UTF-8", "windows-1251", boost::locale::conv::stop) == "Привет");
    const auto& collator = std::use_facet<boost::locale::collator<char>>(locale);
    BOOST_TEST(collator.compare(boost::locale::collate_level::primary, "resume", "résumé") == 0);
    std::ostringstream formatted;
    formatted.imbue(locale);
    formatted << boost::locale::as::number << std::fixed << std::setprecision(1) << 12345.5;
    BOOST_TEST(formatted.str() == "12,345.5");
    double parsed = 0;
    std::istringstream input("12,345.5");
    input.imbue(locale);
    input >> boost::locale::as::number >> parsed;
    BOOST_REQUIRE(!input.fail());
    BOOST_TEST(parsed == 12345.5);
}
#endif
