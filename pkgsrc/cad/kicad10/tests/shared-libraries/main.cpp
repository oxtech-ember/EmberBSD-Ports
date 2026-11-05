#include <clipper2/clipper.h>
#include <argparse/argparse.hpp>
#include <sul/dynamic_bitset.hpp>
#include <fast_float/fast_float.h>
#include <fmt/format.h>
#include <nlohmann/json.hpp>
#include <nanosvg.h>
#include <nanodbc/nanodbc.h>
#include <pybind11/embed.h>
#include <tl/expected.hpp>

#include <cstdint>
#include <string_view>
#include <system_error>

#ifndef USINGZ
#error "KiCad requires the Clipper2 Z-coordinate interface"
#endif

int main()
{
    pybind11::scoped_interpreter python;
    if (!Py_IsInitialized())
        return 6;
    nanodbc::connection database;
    if (database.connected())
        return 7;
    argparse::ArgumentParser arguments("kicad-library-consumer");
    sul::dynamic_bitset<> bits(128);
    bits.set(4);
    bits.set(96);
    if (bits.count() != 2)
        return 8;
    using namespace Clipper2Lib;

    static_assert(sizeof(Point64) == 3 * sizeof(std::int64_t));

    Path64 path;
    path.emplace_back(0, 0, 7);
    path.emplace_back(20, 0, 8);
    path.emplace_back(20, 20, 9);
    path.emplace_back(0, 20, 10);
    Paths64 result = Union(Paths64{path}, FillRule::NonZero);
    if (result.empty())
        return 1;

    constexpr std::string_view number = "12.5";
    double parsed = 0;
    auto conversion = fast_float::from_chars(
        number.data(), number.data() + number.size(), parsed);
    if (conversion.ec != std::errc{} || parsed != 12.5)
        return 2;

    const auto message = fmt::format("value={:.1f}", parsed);
    char svg_document[] = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"2\" height=\"3\"><rect width=\"2\" height=\"3\"/></svg>";
    NSVGimage* svg = nsvgParse(svg_document, "px", 96.0f);
    if (!svg || svg->width != 2.0f || svg->height != 3.0f)
        return 5;
    nsvgDelete(svg);
    nlohmann::json document = {{"value", parsed}, {"message", message}};
    tl::expected<int, int> accepted = 4;
    static_assert(sizeof(pybind11::handle) == sizeof(void *));
    if (!accepted || *accepted != 4)
        return 3;
    return document.at("message") == "value=12.5" ? 0 : 4;
}
