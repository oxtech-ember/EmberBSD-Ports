// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Verify installed public HDR image APIs.
#include <OpenEXR/ImfCompression.h>
#include <OpenEXR/ImfChannelList.h>
#include <OpenEXR/ImfFrameBuffer.h>
#include <OpenEXR/ImfHeader.h>
#include <OpenEXR/ImfInputFile.h>
#include <OpenEXR/ImfOutputFile.h>
#include <OpenEXR/ImfRgbaFile.h>
#include <OpenEXR/ImfThreading.h>
#include <OpenEXR/openexr.h>
#include <Imath/half.h>
#include <array>
#include <cstdio>
#include <exception>
#include <filesystem>
#include <stdexcept>
#include <string>

namespace exr = OPENEXR_IMF_NAMESPACE;
namespace {
constexpr int width = 64;
constexpr int height = 32;
constexpr std::size_t count = static_cast<std::size_t>(width) * height;
constexpr float float_offset = 1.0f / 16777216.0f;

void check(bool valid, const char* message)
{
    if (!valid)
        throw std::runtime_error(message);
}

exr::Rgba value(std::size_t index)
{
    const int x = static_cast<int>(index % width);
    const int y = static_cast<int>(index / width);
    // All four half values are exact binary fractions, including HDR and negatives.
    return exr::Rgba((x - 32) / 4.0f, (y - 16) / 8.0f,
                     (x + y) / 2.0f, 1.0f);
}

void roundtrip(const std::filesystem::path& directory, exr::Compression compression)
{
    std::string name;
    exr::getCompressionNameFromId(compression, name);
    const std::string path = (directory / (name + ".exr")).string();
    std::array<exr::Rgba, count> pixels{};
    for (std::size_t i = 0; i != count; ++i)
        pixels[i] = value(i);
    exr::Header header(width, height);
    header.compression() = compression;
    {
        exr::RgbaOutputFile file(path.c_str(), header, exr::WRITE_RGBA);
        file.setFrameBuffer(pixels.data(), 1, width);
        file.writePixels(height);
    }
    pixels.fill(exr::Rgba(0, 0, 0, 0));
    {
        exr::RgbaInputFile file(path.c_str());
        const auto window = file.dataWindow();
        check(window.min.x == 0 && window.min.y == 0 &&
              window.max.x == width - 1 && window.max.y == height - 1,
              "Incorrect data window");
        check(file.header().compression() == compression, "Incorrect compression metadata");
        check(file.channels() == exr::WRITE_RGBA, "Incorrect RGBA channels");
        file.setFrameBuffer(pixels.data(), 1, width);
        file.readPixels(0, height - 1);
    }
    for (std::size_t i = 0; i != count; ++i) {
        const exr::Rgba expected = value(i);
        check(pixels[i].r.bits() == expected.r.bits() &&
              pixels[i].g.bits() == expected.g.bits() &&
              pixels[i].b.bits() == expected.b.bits() &&
              pixels[i].a.bits() == expected.a.bits(), "HDR pixel round trip changed a half value");
    }
    std::printf("%s: %zu exact RGBA pixels PASS\n", name.c_str(), count);
}

void float_roundtrip(const std::filesystem::path& directory)
{
    const std::string path = (directory / "float-zstd.exr").string();
    std::array<float, count> pixels{};
    for (std::size_t i = 0; i != count; ++i)
        pixels[i] = (static_cast<float>(i) - 1024.0f) / 65536.0f + float_offset;
    exr::Header header(width, height);
    header.compression() = exr::ZSTD_COMPRESSION;
    header.channels().insert("Y", exr::Channel(exr::FLOAT));
    exr::FrameBuffer buffer;
    buffer.insert("Y", exr::Slice(exr::FLOAT, reinterpret_cast<char*>(pixels.data()),
                                  sizeof(float), sizeof(float) * width));
    {
        exr::OutputFile file(path.c_str(), header);
        file.setFrameBuffer(buffer);
        file.writePixels(height);
    }
    pixels.fill(0.0f);
    {
        exr::InputFile file(path.c_str());
        const auto window = file.header().dataWindow();
        check(window.min.x == 0 && window.min.y == 0 &&
              window.max.x == width - 1 && window.max.y == height - 1,
              "Incorrect float data window");
        check(file.header().compression() == exr::ZSTD_COMPRESSION,
              "Incorrect float compression metadata");
        const exr::Channel* channel = file.header().channels().findChannel("Y");
        check(channel && channel->type == exr::FLOAT, "Incorrect float channel type");
        file.setFrameBuffer(buffer);
        file.readPixels(0, height - 1);
    }
    for (std::size_t i = 0; i != count; ++i)
        check(pixels[i] == (static_cast<float>(i) - 1024.0f) / 65536.0f + float_offset,
              "Float channel round trip changed a value");
    std::printf("zstd: %zu exact float pixels PASS\n", count);
}
}

int main(int argc, char** argv)
{
    if (argc != 2)
        return 2;
    try {
        const std::filesystem::path directory(argv[1]);
        check(directory.is_absolute() && std::filesystem::is_directory(directory) &&
              std::filesystem::is_empty(directory), "Use a new empty absolute output directory");
        int major = 0, minor = 0, patch = 0;
        const char* extra = nullptr;
        exr_get_library_version(&major, &minor, &patch, &extra);
        check(major == 3 && minor == 5 && patch == 2, "Expected OpenEXR 3.5.2 runtime");
        exr::setGlobalThreadCount(2);
        const exr::Compression methods[] = {exr::NO_COMPRESSION, exr::RLE_COMPRESSION,
            exr::ZIPS_COMPRESSION, exr::ZIP_COMPRESSION, exr::PIZ_COMPRESSION,
            exr::HTJ2K32_COMPRESSION, exr::HTJ2K256_COMPRESSION, exr::ZSTD_COMPRESSION};
        for (const auto method : methods)
            roundtrip(directory, method);
        float_roundtrip(directory);
        exr::setGlobalThreadCount(0);
        std::puts("OpenEXR installed API: PASS");
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "OpenEXR installed API: %s\n", error.what());
        exr::setGlobalThreadCount(0);
        return 1;
    }
}
