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

bool guardsAndPaddingAreFor(const std::vector<unsigned char> &storage,
                            std::size_t offset, int width, int height, int stride,
                            unsigned char value)
{
    for (int i = 0; i < guardSize; ++i) {
        if (storage[static_cast<std::size_t>(i)] != value
            || storage[offset + static_cast<std::size_t>(height * stride)
                       + static_cast<std::size_t>(i)] != value)
            return false;
    }
    const int rowPadding = stride - width * pixelBytes;
    for (int y = 0; y < height; ++y) {
        const std::size_t row = offset + static_cast<std::size_t>(y * stride);
        for (int i = 0; i < rowPadding; ++i) {
            if (storage[row + static_cast<std::size_t>(width * pixelBytes)
                        + static_cast<std::size_t>(i)] != value)
                return false;
        }
    }
    return true;
}

bool guardsAndPaddingAre(const std::vector<unsigned char> &storage, unsigned char value)
{
    return guardsAndPaddingAreFor(storage, guardSize, nativeWidth, nativeHeight,
                                  nativeStride, value);
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

QPoint sourcePointForNative(Rotation rotation, int x, int y,
                            int bigNativeWidth, int bigNativeHeight)
{
    switch (rotation) {
    case Rotation::R0: return QPoint(x, y);
    case Rotation::R90: return QPoint(y, bigNativeWidth - 1 - x);
    case Rotation::R180:
        return QPoint(bigNativeWidth - 1 - x, bigNativeHeight - 1 - y);
    case Rotation::R270: return QPoint(bigNativeHeight - 1 - y, x);
    }
    return QPoint(-1, -1);
}

QColor coordinateColor(int x, int y)
{
    return QColor(x + 1, y + 1, (x * 131 + y * 17) & 0xff);
}

void testLargeDisjointDamage(QImage::Format format, PixelFormat pixelFormat)
{
    constexpr int bigNativeWidth = 97;
    constexpr int bigNativeHeight = 83;
    constexpr int bigNativeStride = bigNativeWidth * pixelBytes + 12;
    constexpr int offset = 16;
    constexpr unsigned char sentinel = 0xA7;
    const std::array rotations{Rotation::R0, Rotation::R90,
                               Rotation::R180, Rotation::R270};

    for (Rotation rotation : rotations) {
        const QSize logicalSize = (rotation == Rotation::R90 || rotation == Rotation::R270)
            ? QSize(bigNativeHeight, bigNativeWidth) : QSize(bigNativeWidth, bigNativeHeight);
        const QRect first(-3, 7, 43, 39);
        const QRect second(logicalSize.width() - 41,
                           logicalSize.height() - 44, 36, 37);
        QRegion damage(first);
        damage += second;

        const int sourceStride = logicalSize.width() * pixelBytes + 12;
        std::vector<unsigned char> sourceStorage(
            static_cast<std::size_t>(sourceStride)
                * static_cast<std::size_t>(logicalSize.height()), 0x5D);
        QImage source(sourceStorage.data(), logicalSize.width(), logicalSize.height(),
                      sourceStride, QImage::Format_RGB32);
        for (int y = 0; y < logicalSize.height(); ++y) {
            for (int x = 0; x < logicalSize.width(); ++x)
                source.setPixelColor(x, y, coordinateColor(x, y));
        }

        constexpr std::size_t framebufferSize =
            static_cast<std::size_t>(bigNativeStride) * bigNativeHeight;
        std::vector<unsigned char> storage(
            static_cast<std::size_t>(offset) + framebufferSize + guardSize, sentinel);
        QImage destination(storage.data() + offset, bigNativeWidth, bigNativeHeight,
                           bigNativeStride, format);
        for (int y = 0; y < bigNativeHeight; ++y) {
            for (int x = 0; x < bigNativeWidth; ++x)
                destination.setPixelColor(x, y, QColor::fromRgb(background));
        }
        const Layout layout{storage.size(), offset, bigNativeWidth, bigNativeHeight,
                            bigNativeStride, pixelFormat};

        check(QBsdFb::blit(destination, source, layout, rotation, damage),
              "large disjoint damage is blitted for every rotation");
        for (int y = 0; y < bigNativeHeight; ++y) {
            for (int x = 0; x < bigNativeWidth; ++x) {
                const QPoint sourcePoint = sourcePointForNative(
                    rotation, x, y, bigNativeWidth, bigNativeHeight);
                const bool touched = damage.contains(sourcePoint);
                const QColor expected = touched
                    ? coordinateColor(sourcePoint.x(), sourcePoint.y())
                    : QColor::fromRgb(background);
                check(destination.pixelColor(x, y) == expected,
                      "multi-rect blit preserves gap and maps source pixels correctly");
            }
        }
        check(guardsAndPaddingAreFor(storage, offset, bigNativeWidth, bigNativeHeight,
                                     bigNativeStride, sentinel),
              "multi-rect blit preserves guards and padded row bytes");
        for (int y = 0; y < logicalSize.height(); ++y) {
            for (int x = logicalSize.width() * pixelBytes; x < sourceStride; ++x) {
                check(sourceStorage[static_cast<std::size_t>(y)
                                    * static_cast<std::size_t>(sourceStride)
                                    + static_cast<std::size_t>(x)] == 0x5D,
                      "multi-rect blit leaves padded source rows unchanged");
            }
        }
    }
}

void testMixedLargeAndTinyDamage()
{
    constexpr int bigNativeWidth = 97;
    constexpr int bigNativeHeight = 83;
    constexpr int bigNativeStride = bigNativeWidth * pixelBytes + 12;
    constexpr int offset = 16;
    constexpr unsigned char sentinel = 0xA7;
    constexpr std::size_t framebufferSize =
        static_cast<std::size_t>(bigNativeStride) * bigNativeHeight;
    const std::array rotations{Rotation::R90, Rotation::R270};

    for (Rotation rotation : rotations) {
        const QSize logicalSize(bigNativeHeight, bigNativeWidth);
        const QRect large(7, 5, 39, 41);
        const QRect tiny(logicalSize.width() - 1, logicalSize.height() - 1, 1, 1);
        QRegion damage(large);
        damage += tiny;

        QImage source(logicalSize, QImage::Format_RGB32);
        for (int y = 0; y < logicalSize.height(); ++y) {
            for (int x = 0; x < logicalSize.width(); ++x)
                source.setPixelColor(x, y, coordinateColor(x, y));
        }
        std::vector<unsigned char> storage(
            static_cast<std::size_t>(offset) + framebufferSize + guardSize, sentinel);
        QImage destination(storage.data() + offset, bigNativeWidth, bigNativeHeight,
                           bigNativeStride, QImage::Format_RGB32);
        for (int y = 0; y < bigNativeHeight; ++y) {
            for (int x = 0; x < bigNativeWidth; ++x)
                destination.setPixelColor(x, y, QColor::fromRgb(background));
        }
        const Layout layout{storage.size(), offset, bigNativeWidth, bigNativeHeight,
                            bigNativeStride, PixelFormat::Xrgb8888};

        check(QBsdFb::blit(destination, source, layout, rotation, damage),
              "mixed large and tiny damage is blitted");
        for (int y = 0; y < bigNativeHeight; ++y) {
            for (int x = 0; x < bigNativeWidth; ++x) {
                const QPoint sourcePoint = sourcePointForNative(
                    rotation, x, y, bigNativeWidth, bigNativeHeight);
                const bool touched = damage.contains(sourcePoint);
                const QColor expected = touched
                    ? coordinateColor(sourcePoint.x(), sourcePoint.y())
                    : QColor::fromRgb(background);
                check(destination.pixelColor(x, y) == expected,
                      "mixed damage maps pixels and preserves untouched gaps");
            }
        }
        check(guardsAndPaddingAreFor(storage, offset, bigNativeWidth, bigNativeHeight,
                                     bigNativeStride, sentinel),
              "mixed damage preserves guards and padded row bytes");
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

void testInvalidLayoutIsRejectedBeforePainting()
{
    std::vector<unsigned char> storage(storageSize, 0xA7);
    QImage destination(storage.data() + guardSize, nativeWidth, nativeHeight,
                       nativeStride, QImage::Format_RGB32);
    const QColor untouched = QColor::fromRgb(background);
    initializeDestination(destination, untouched);
    const QImage source = makeSource(QSize(nativeWidth, nativeHeight));
    Layout shortLayout{guardSize + framebufferBytes - 1, guardSize,
                       nativeWidth, nativeHeight, nativeStride,
                       PixelFormat::Xrgb8888};

    check(!QBsdFb::blit(destination, source, shortLayout, Rotation::R0,
                        QRegion(QRect(0, 0, nativeWidth, nativeHeight))),
          "layout shorter than its destination storage is rejected");
    verifyUnchanged(destination, untouched,
                    "invalid layout leaves framebuffer pixels unchanged");
    check(guardsAndPaddingAre(storage, 0xA7),
          "invalid layout preserves framebuffer guards and padding");
}

void testOverlappingImagesMatchIndependentPixelOracle()
{
    constexpr int logicalWidth = 7;
    constexpr int logicalHeight = 6;
    constexpr int sourceStride = logicalWidth * pixelBytes + 8;
    constexpr int rotatedWidth = logicalHeight;
    constexpr int rotatedHeight = logicalWidth;
    constexpr int destinationStride = rotatedWidth * pixelBytes + 12;
    constexpr std::size_t sourceOffset = 8;
    constexpr std::size_t destinationOffset = 32;
    constexpr unsigned char sentinel = 0xA7;
    constexpr std::size_t destinationBytes =
        static_cast<std::size_t>(destinationStride) * rotatedHeight;
    constexpr std::size_t storageBytes = destinationOffset + destinationBytes + guardSize;

    std::vector<unsigned char> storage(storageBytes, sentinel);
    QImage source(storage.data() + sourceOffset, logicalWidth, logicalHeight,
                  sourceStride, QImage::Format_RGB32);
    QImage destination(storage.data() + destinationOffset, rotatedWidth, rotatedHeight,
                       destinationStride, QImage::Format_RGB32);
    check(!source.isNull() && !destination.isNull(),
          "overlapping external source and destination images are valid");
    for (int y = 0; y < logicalHeight; ++y) {
        for (int x = 0; x < logicalWidth; ++x)
            source.setPixelColor(x, y, coordinateColor(x, y));
    }
    for (int y = 0; y < rotatedHeight; ++y) {
        for (int x = 0; x < rotatedWidth; ++x)
            destination.setPixelColor(x, y, QColor::fromRgb(background));
    }
    std::vector<unsigned char> referenceStorage = storage;
    QImage referenceSource(referenceStorage.data() + sourceOffset, logicalWidth,
                           logicalHeight, sourceStride, QImage::Format_RGB32);
    QImage referenceDestination(referenceStorage.data() + destinationOffset,
                                rotatedWidth, rotatedHeight, destinationStride,
                                QImage::Format_RGB32);
    QPainter referencePainter(&referenceDestination);
    referencePainter.setCompositionMode(QPainter::CompositionMode_Source);
    referencePainter.setClipRect(QRect(0, 0, rotatedWidth, rotatedHeight));
    referencePainter.translate(rotatedWidth, 0);
    referencePainter.rotate(90);
    referencePainter.drawImage(QPoint(0, 0), referenceSource);
    check(referencePainter.end(), "independent QPainter alias oracle completes");
    std::vector<unsigned char> destinationPadding;
    for (int y = 0; y < rotatedHeight; ++y) {
        const std::size_t row = destinationOffset
            + static_cast<std::size_t>(y) * destinationStride
            + static_cast<std::size_t>(rotatedWidth) * pixelBytes;
        for (int x = 0; x < destinationStride - rotatedWidth * pixelBytes; ++x)
            destinationPadding.push_back(storage[row + static_cast<std::size_t>(x)]);
    }
    const Layout layout{storage.size(), destinationOffset, rotatedWidth, rotatedHeight,
                        destinationStride, PixelFormat::Xrgb8888};

    check(QBsdFb::blit(destination, source, layout, Rotation::R90,
                       QRegion(QRect(0, 0, logicalWidth, logicalHeight))),
          "overlapping images retain the existing accepted blit behavior");
    for (int y = 0; y < rotatedHeight; ++y) {
        for (int x = 0; x < rotatedWidth; ++x) {
            check(destination.pixelColor(x, y)
                      == referenceDestination.pixelColor(x, y),
                  "overlapping blit matches independent QPainter behavior");
        }
    }
    std::size_t paddingIndex = 0;
    for (int y = 0; y < rotatedHeight; ++y) {
        const std::size_t row = destinationOffset
            + static_cast<std::size_t>(y) * destinationStride
            + static_cast<std::size_t>(rotatedWidth) * pixelBytes;
        for (int x = 0; x < destinationStride - rotatedWidth * pixelBytes; ++x) {
            check(storage[row + static_cast<std::size_t>(x)]
                      == destinationPadding[paddingIndex],
                  "overlapping blit preserves destination row padding");
            ++paddingIndex;
        }
    }
}

} // namespace

int main()
{
    testRotationAndDamage(QImage::Format_RGB32, PixelFormat::Xrgb8888);
    testRotationAndDamage(QImage::Format_RGBX8888, PixelFormat::Xbgr8888);
    testLargeDisjointDamage(QImage::Format_RGB32, PixelFormat::Xrgb8888);
    testLargeDisjointDamage(QImage::Format_RGBX8888, PixelFormat::Xbgr8888);
    testMixedLargeAndTinyDamage();
    testInvalidInputsAreRejectedWithoutChangingPixels(
        QImage::Format_RGB32, PixelFormat::Xrgb8888);
    testInvalidInputsAreRejectedWithoutChangingPixels(
        QImage::Format_RGBX8888, PixelFormat::Xbgr8888);
    testInvalidLayoutIsRejectedBeforePainting();
    testOverlappingImagesMatchIndependentPixelOracle();
    return failures == 0 ? 0 : 1;
}
