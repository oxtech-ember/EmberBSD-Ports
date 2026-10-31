// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).

#include "qbsdfbblit_p.h"

#include <QColor>
#include <QImage>
#include <QRegion>
#include <QtGlobal>

#include <algorithm>
#include <array>
#include <iostream>
#include <vector>

namespace {

using QBsdFb::Layout;
using QBsdFb::PixelFormat;
using QBsdFb::Rotation;

constexpr int nativeWidth = 2;
constexpr int nativeHeight = 3;
constexpr int nativeStride = 16;
constexpr int guardSize = 16;
constexpr int pixelBytes = 4;
constexpr int paddingSize = nativeStride - nativeWidth * pixelBytes;
constexpr std::size_t framebufferBytes = nativeStride * nativeHeight;
constexpr std::size_t storageSize = guardSize + framebufferBytes + guardSize;
constexpr QRgb background = qRgb(193, 167, 83);

struct Fixture {
    Rotation rotation;
    QSize logicalSize;
    std::array<int, 6> sourceIndexForNative;
    std::array<bool, 6> partialDamageForNative;
};

constexpr std::array<Fixture, 4> fixtures{{
    {Rotation::R0, QSize(2, 3), {0, 1, 2, 3, 4, 5},
     {false, false, true, true, true, true}},
    {Rotation::R90, QSize(3, 2), {3, 0, 4, 1, 5, 2},
     {true, false, true, false, false, false}},
    {Rotation::R180, QSize(2, 3), {5, 4, 3, 2, 1, 0},
     {true, true, true, true, false, false}},
    {Rotation::R270, QSize(3, 2), {2, 5, 1, 4, 0, 3},
     {false, false, false, true, false, true}},
}};

int failures = 0;

void check(bool condition, const char *description)
{
    if (!condition) {
        std::cerr << "FAIL: " << description << '\n';
        ++failures;
    }
}

QColor sourceColor(int index)
{
    return QColor(17 + index * 31, 19 + index * 23, 29 + index * 17);
}

QImage makeSource(const QSize &size)
{
    QImage image(size, QImage::Format_RGB32);
    for (int y = 0; y < size.height(); ++y) {
        for (int x = 0; x < size.width(); ++x)
            image.setPixelColor(x, y, sourceColor(y * size.width() + x));
    }
    return image;
}

void initializeDestination(QImage &image, const QColor &color)
{
    for (int y = 0; y < nativeHeight; ++y) {
        for (int x = 0; x < nativeWidth; ++x)
            image.setPixelColor(x, y, color);
    }
}

bool guardsAndPaddingAre(const std::vector<unsigned char> &storage, unsigned char value)
{
    for (int i = 0; i < guardSize; ++i) {
        if (storage[static_cast<std::size_t>(i)] != value
            || storage[guardSize + framebufferBytes + static_cast<std::size_t>(i)] != value)
            return false;
    }
    for (int y = 0; y < nativeHeight; ++y) {
        const std::size_t row = guardSize + static_cast<std::size_t>(y * nativeStride);
        for (int i = 0; i < paddingSize; ++i) {
            if (storage[row + nativeWidth * pixelBytes + static_cast<std::size_t>(i)] != value)
                return false;
        }
    }
    return true;
}

void verifyPixels(const Fixture &fixture, const QImage &destination,
                  const QColor &untouched, bool partial)
{
    for (int y = 0; y < nativeHeight; ++y) {
        for (int x = 0; x < nativeWidth; ++x) {
            const std::size_t nativeIndex = static_cast<std::size_t>(y * nativeWidth + x);
            const QColor expected = !partial || fixture.partialDamageForNative[nativeIndex]
                ? sourceColor(fixture.sourceIndexForNative[nativeIndex]) : untouched;
            check(destination.pixelColor(x, y) == expected,
                  "blit pixel matches independent native-orientation table");
        }
    }
}

void verifyUnchanged(const QImage &destination, const QColor &untouched,
                     const char *description)
{
    for (int y = 0; y < nativeHeight; ++y) {
        for (int x = 0; x < nativeWidth; ++x)
            check(destination.pixelColor(x, y) == untouched, description);
    }
}

void testRotationAndDamage(QImage::Format format, PixelFormat pixelFormat)
{
    for (const Fixture &fixture : fixtures) {
        std::vector<unsigned char> storage(storageSize, 0xA7);
        QImage destination(storage.data() + guardSize, nativeWidth, nativeHeight,
                           nativeStride, format);
        check(!destination.isNull(), "external padded destination image is valid");
        initializeDestination(destination, QColor::fromRgb(background));
        const QImage source = makeSource(fixture.logicalSize);
        const Layout layout{storage.size(), guardSize, nativeWidth, nativeHeight,
                            nativeStride, pixelFormat};

        check(QBsdFb::blit(destination, source, layout, fixture.rotation,
                           QRegion(QRect(0, 0, fixture.logicalSize.width(),
                                         fixture.logicalSize.height()))),
              "full logical damage is blitted");
        verifyPixels(fixture, destination, QColor::fromRgb(background), false);
        check(guardsAndPaddingAre(storage, 0xA7),
              "full blit preserves prefix, suffix, and padded row bytes");

        std::fill(storage.begin(), storage.end(), 0xA7);
        initializeDestination(destination, QColor::fromRgb(background));
        check(QBsdFb::blit(destination, source, layout, fixture.rotation,
                           QRegion(QRect(-1, 1, 3, 2))),
              "partially clipped logical damage is blitted");
        verifyPixels(fixture, destination, QColor::fromRgb(background), true);
        check(guardsAndPaddingAre(storage, 0xA7),
              "partial blit preserves prefix, suffix, and padded row bytes");
    }
}

void testInvalidInputsAreRejectedWithoutChangingPixels(QImage::Format format,
                                                        PixelFormat pixelFormat)
{
    std::vector<unsigned char> storage(storageSize, 0xA7);
    QImage destination(storage.data() + guardSize, nativeWidth, nativeHeight,
                       nativeStride, format);
    const QColor untouched = QColor::fromRgb(background);
    initializeDestination(destination, untouched);
    const QImage source = makeSource(QSize(nativeWidth, nativeHeight));
    const Layout layout{storage.size(), guardSize, nativeWidth, nativeHeight,
                        nativeStride, pixelFormat};

    const QImage wrongSizeSource = makeSource(QSize(1, 1));
    check(!QBsdFb::blit(destination, wrongSizeSource, layout, Rotation::R0,
                        QRegion(QRect(0, 0, nativeWidth, nativeHeight))),
          "source geometry mismatch is rejected");
    verifyUnchanged(destination, untouched, "wrong source geometry leaves pixels unchanged");

    check(!QBsdFb::blit(destination, source, layout, Rotation::R0, QRegion()),
          "empty damage is rejected");
    verifyUnchanged(destination, untouched, "empty damage leaves pixels unchanged");
    check(!QBsdFb::blit(destination, source, layout, Rotation::R0,
                        QRegion(QRect(nativeWidth + 2, nativeHeight + 2, 1, 1))),
          "outside damage is rejected");
    verifyUnchanged(destination, untouched, "outside damage leaves pixels unchanged");

    QImage sharedDestination = destination;
    check(!destination.isDetached(), "shared destination fixture is implicitly shared");
    check(!QBsdFb::blit(destination, source, layout, Rotation::R0,
                        QRegion(QRect(0, 0, nativeWidth, nativeHeight))),
          "shared destination is rejected without detaching the framebuffer view");
    verifyUnchanged(destination, untouched, "shared destination remains unchanged");
    verifyUnchanged(sharedDestination, untouched, "shared alias remains unchanged");
    check(guardsAndPaddingAre(storage, 0xA7),
          "rejected inputs preserve prefix, suffix, and padded row bytes");
}

} // namespace

int main()
{
    testRotationAndDamage(QImage::Format_RGB32, PixelFormat::Xrgb8888);
    testRotationAndDamage(QImage::Format_RGBX8888, PixelFormat::Xbgr8888);
    testInvalidInputsAreRejectedWithoutChangingPixels(
        QImage::Format_RGB32, PixelFormat::Xrgb8888);
    testInvalidInputsAreRejectedWithoutChangingPixels(
        QImage::Format_RGBX8888, PixelFormat::Xbgr8888);
    return failures == 0 ? 0 : 1;
}
