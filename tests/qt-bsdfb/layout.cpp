// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).

#include "qbsdfblayout_p.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>

namespace {

using QBsdFb::FrameInfo;
using QBsdFb::Layout;
using QBsdFb::PixelFormat;
using QBsdFb::Point;
using QBsdFb::Rect;
using QBsdFb::Rotation;
using QBsdFb::Size;

int failures = 0;

void check(bool condition, const char *name)
{
    if (!condition) {
        std::cerr << "FAIL: " << name << '\n';
        ++failures;
    }
}

bool same(Point a, Point b)
{
    return a.x == b.x && a.y == b.y;
}

bool same(Rect a, Rect b)
{
    return a.x == b.x && a.y == b.y
        && a.width == b.width && a.height == b.height;
}

FrameInfo sampleRgb()
{
    FrameInfo info{};
    info.fbsize = 4096000;
    info.offset = 256;
    info.width = 800;
    info.height = 1280;
    info.stride = 3200;
    info.bpp = 32;
    info.pixelType = 0;
    info.flags = 1;
    info.redOffset = 16;
    info.redSize = 8;
    info.greenOffset = 8;
    info.greenSize = 8;
    info.blueOffset = 0;
    info.blueSize = 8;
    info.alphaOffset = 0;
    info.alphaSize = 0;
    return info;
}

void testLayout()
{
    Layout layout{};
    const FrameInfo info = sampleRgb();
    check(QBsdFb::makeLayout(info, layout), "accept RGB888-in-32-bit sample");
    check(layout.mapLength == 4096256, "mapping includes prefix and raster capacity");
    check(layout.dataOffset == 256, "pixel base uses framebuffer prefix");
    check(layout.nativeWidth == 800 && layout.nativeHeight == 1280,
          "native dimensions preserved");
    check(layout.stride == 3200, "native stride preserved");
    check(layout.format == PixelFormat::Xrgb8888, "red-high layout selects Xrgb8888");

    FrameInfo padded = info;
    padded.stride = 3216;
    padded.fbsize = static_cast<std::uint64_t>(padded.stride) * padded.height;
    check(QBsdFb::makeLayout(padded, layout), "accept padded rows with full capacity");
    check(layout.stride == 3216, "padded stride is not collapsed to width times four");

    FrameInfo bgr = info;
    bgr.redOffset = 0;
    bgr.blueOffset = 16;
    check(QBsdFb::makeLayout(bgr, layout), "accept reversed red and blue channels");
    check(layout.format == PixelFormat::Xbgr8888, "red-low layout selects Xbgr8888");

    FrameInfo unusedAlphaOffset = info;
    unusedAlphaOffset.alphaOffset = 31;
    check(QBsdFb::makeLayout(unusedAlphaOffset, layout),
          "ignore alpha offset when alpha channel size is zero");

    FrameInfo noFlags = info;
    noFlags.flags = 0;
    check(QBsdFb::makeLayout(noFlags, layout), "accept zero framebuffer flags");

    FrameInfo ptrdiffBoundary = info;
    ptrdiffBoundary.fbsize = static_cast<std::uint64_t>(
        std::numeric_limits<std::ptrdiff_t>::max()) - ptrdiffBoundary.offset;
    check(QBsdFb::makeLayout(ptrdiffBoundary, layout),
          "accept map length equal to PTRDIFF_MAX");
    check(layout.mapLength == static_cast<std::size_t>(
              std::numeric_limits<std::ptrdiff_t>::max()),
          "preserve the PTRDIFF_MAX map length");

    Layout sentinel{};
    sentinel.mapLength = 77;
    sentinel.dataOffset = 11;
    sentinel.nativeWidth = 7;
    sentinel.nativeHeight = 9;
    sentinel.stride = 28;
    sentinel.format = PixelFormat::Xrgb8888;
    const auto rejectsWithoutChangingOutput = [&](const FrameInfo &invalid, const char *name) {
        Layout output = sentinel;
        check(!QBsdFb::makeLayout(invalid, output), name);
        check(output.mapLength == sentinel.mapLength
                  && output.dataOffset == sentinel.dataOffset
                  && output.nativeWidth == sentinel.nativeWidth
                  && output.nativeHeight == sentinel.nativeHeight
                  && output.stride == sentinel.stride
                  && output.format == sentinel.format,
              "failed layout leaves output unchanged");
    };

    FrameInfo invalid = info;
    invalid.width = 0;
    rejectsWithoutChangingOutput(invalid, "reject zero width");
    invalid = info;
    invalid.height = 0;
    rejectsWithoutChangingOutput(invalid, "reject zero height");
    invalid = info;
    invalid.bpp = 24;
    rejectsWithoutChangingOutput(invalid, "reject non-32-bit pixels");
    invalid = info;
    invalid.pixelType = 1;
    rejectsWithoutChangingOutput(invalid, "reject non-RGB pixel type");
    invalid = info;
    invalid.flags = 2;
    rejectsWithoutChangingOutput(invalid, "reject split framebuffer flags");
    invalid = info;
    invalid.flags = 4;
    rejectsWithoutChangingOutput(invalid, "reject unknown framebuffer flags");
    invalid = info;
    invalid.redSize = 5;
    rejectsWithoutChangingOutput(invalid, "reject unsupported channel width");
    invalid = info;
    invalid.greenOffset = 16;
    rejectsWithoutChangingOutput(invalid, "reject overlapping channels");
    invalid = info;
    invalid.alphaSize = 8;
    rejectsWithoutChangingOutput(invalid, "reject alpha channel");
    invalid = info;
    invalid.stride = 3196;
    rejectsWithoutChangingOutput(invalid, "reject stride smaller than visible row");
    invalid = info;
    invalid.stride = 3202;
    invalid.fbsize = static_cast<std::uint64_t>(invalid.stride) * invalid.height;
    rejectsWithoutChangingOutput(invalid, "reject stride not aligned to 32-bit pixels");
    invalid = info;
    invalid.offset = 258;
    rejectsWithoutChangingOutput(invalid, "reject pixel data offset not aligned to 32-bit pixels");
    invalid = info;
    invalid.fbsize = 4095999;
    rejectsWithoutChangingOutput(invalid, "reject capacity smaller than all rows");
    invalid = info;
    invalid.width = static_cast<std::uint32_t>(std::numeric_limits<int>::max()) + 1U;
    rejectsWithoutChangingOutput(invalid, "reject dimensions outside Qt int range");
    invalid = info;
    invalid.stride = static_cast<std::uint32_t>(std::numeric_limits<int>::max()) + 1U;
    rejectsWithoutChangingOutput(invalid, "reject stride outside Qt int range");
    invalid = info;
    invalid.fbsize = static_cast<std::uint64_t>(std::numeric_limits<std::size_t>::max());
    invalid.offset = 4;
    rejectsWithoutChangingOutput(invalid, "reject map length overflow");
    invalid = info;
    invalid.fbsize = static_cast<std::uint64_t>(
        std::numeric_limits<std::ptrdiff_t>::max()) + 1U;
    invalid.offset = 0;
    rejectsWithoutChangingOutput(invalid, "reject map length above PTRDIFF_MAX");
}

void testRotations()
{
    Layout layout{};
    check(QBsdFb::makeLayout(sampleRgb(), layout), "rotation fixture is valid");

    struct CornerCase {
        Rotation rotation = Rotation::R0;
        Size logicalSize{};
        std::array<Point, 4> logical{};
        std::array<Point, 4> native{};
    };
    const std::array cases{
        CornerCase{Rotation::R0, {800, 1280},
                   {{{0, 0}, {799, 0}, {0, 1279}, {799, 1279}}},
                   {{{0, 0}, {799, 0}, {0, 1279}, {799, 1279}}}},
        CornerCase{Rotation::R90, {1280, 800},
                   {{{0, 0}, {1279, 0}, {0, 799}, {1279, 799}}},
                   {{{799, 0}, {799, 1279}, {0, 0}, {0, 1279}}}},
        CornerCase{Rotation::R180, {800, 1280},
                   {{{0, 0}, {799, 0}, {0, 1279}, {799, 1279}}},
                   {{{799, 1279}, {0, 1279}, {799, 0}, {0, 0}}}},
        CornerCase{Rotation::R270, {1280, 800},
                   {{{0, 0}, {1279, 0}, {0, 799}, {1279, 799}}},
                   {{{0, 1279}, {0, 0}, {799, 1279}, {799, 0}}}},
    };

    for (const CornerCase &test : cases) {
        check(QBsdFb::logicalSize(layout, test.rotation).width == test.logicalSize.width
                  && QBsdFb::logicalSize(layout, test.rotation).height == test.logicalSize.height,
              "rotation reports expected logical size");
        for (std::size_t i = 0; i < test.logical.size(); ++i) {
            const auto native = QBsdFb::nativeFromLogical(layout, test.rotation,
                                                           test.logical[i]);
            check(native.has_value() && same(*native, test.native[i]),
                  "corner maps to independently specified native coordinate");
            const auto logical = QBsdFb::logicalFromNative(layout, test.rotation,
                                                            test.native[i]);
            check(logical.has_value() && same(*logical, test.logical[i]),
                  "corner mapping has independently specified inverse");
        }

        const int logicalWidth = test.logicalSize.width;
        const int logicalHeight = test.logicalSize.height;
        bool allPointsRoundTrip = true;
        for (int y = 0; y < logicalHeight; ++y) {
            for (int x = 0; x < logicalWidth; ++x) {
                const Point point{x, y};
                const auto native = QBsdFb::nativeFromLogical(layout, test.rotation, point);
                if (!native) {
                    allPointsRoundTrip = false;
                    continue;
                }
                const auto inverse = QBsdFb::logicalFromNative(layout, test.rotation, *native);
                if (!inverse || !same(*inverse, point))
                    allPointsRoundTrip = false;
            }
        }
        check(allPointsRoundTrip, "all logical points round-trip for each rotation");
    }

    check(!QBsdFb::nativeFromLogical(layout, Rotation::R90, {-1, 0}).has_value(),
          "reject negative logical coordinate");
    check(!QBsdFb::nativeFromLogical(layout, Rotation::R0, {800, 0}).has_value(),
          "reject logical coordinate at right edge");
    check(!QBsdFb::logicalFromNative(layout, Rotation::R180, {0, 1280}).has_value(),
          "reject native coordinate at bottom edge");
}

void testDamageBounds()
{
    Layout layout{};
    check(QBsdFb::makeLayout(sampleRgb(), layout), "damage fixture is valid");

    const auto clipped = QBsdFb::nativeBounds(layout, Rotation::R90, {-2, 1, 5, 3});
    check(clipped.has_value() && same(*clipped, {796, 0, 3, 3}),
          "clip logical damage then rotate its pixel bounds");

    const auto interior = QBsdFb::nativeBounds(layout, Rotation::R0, {10, 20, 4, 3});
    check(interior.has_value() && same(*interior, {10, 20, 4, 3}),
          "unrotated interior damage is preserved");

    check(!QBsdFb::nativeBounds(layout, Rotation::R0, {0, 0, 0, 5}).has_value(),
          "zero-width damage is empty");
    check(!QBsdFb::nativeBounds(layout, Rotation::R0, {0, 0, 5, -1}).has_value(),
          "negative-height damage is empty");
    check(!QBsdFb::nativeBounds(layout, Rotation::R0, {900, 0, 5, 5}).has_value(),
          "fully outside damage is empty");
    check(!QBsdFb::nativeBounds(layout, Rotation::R0,
                                {std::numeric_limits<int>::max() - 2, 0, 10, 1})
               .has_value(),
          "damage arithmetic does not overflow int");
}

} // namespace

int main()
{
    testLayout();
    testRotations();
    testDamageBounds();
    if (failures != 0)
        std::cerr << failures << " framebuffer layout checks failed\n";
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
