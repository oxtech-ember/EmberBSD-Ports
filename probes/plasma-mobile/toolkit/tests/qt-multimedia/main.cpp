// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Real player frames; software decoding only.
#include <QDebug>
#include <QFile>
#include <QGuiApplication>
#include <QMediaPlayer>
#include <QTimer>
#include <QUrl>
#include <QVideoFrame>
#include <QVideoSink>
#include <cstdio>
#include <cstring>
#include <link_elf.h>

// dl_iterate_phdr requires this non-const callback signature.
// cppcheck-suppress constParameterCallback
static int loadedLibrary(dl_phdr_info *info, size_t, void *)
{
    if (info->dlpi_name && *info->dlpi_name)
        std::printf("loaded=%s\n", info->dlpi_name);
    return 0;
}

int main(int argc, char **argv)
{
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    QGuiApplication app(argc, argv);
    const auto args = app.arguments();
    if (args.size() != 4 || (args[3] != "normal" && args[3] != "wrong-pixel"
            && args[3] != "missing")) {
        qCritical() << "Usage: qt-multimedia MOVIE YUV normal|wrong-pixel|missing";
        return 2;
    }
    QFile original(args[2]);
    if (!original.open(QIODevice::ReadOnly))
        return 2;
    QByteArray expected = original.readAll();
    constexpr int frameBytes = 64 * 64 + 2 * 32 * 32;
    if (expected.size() != 4 * frameBytes)
        return 2;
    if (args[3] == "wrong-pixel")
        expected[0] = static_cast<char>(expected[0] ^ 1);
    const bool missing = args[3] == "missing";
    QVideoSink sink;
    QMediaPlayer player;
    int frames = 0;
    qint64 previous = -1;
    bool done = false;
    auto finish = [&](int code, const char *message) {
        if (done)
            return;
        done = true;
        std::printf("%s: %s; frames=%d Qt=%s\n", code ? "FAIL" : "PASS", message, frames, qVersion());
        dl_iterate_phdr(loadedLibrary, nullptr);
        app.exit(code);
    };
    QObject::connect(&sink, &QVideoSink::videoFrameChanged, &app, [&](const QVideoFrame &input) {
        if (done || !input.isValid())
            return;
        QVideoFrame frame(input);
        if (missing || frames >= 4 || frame.size() != QSize(64, 64)
                || frame.pixelFormat() != QVideoFrameFormat::Format_YUV420P
                || frame.startTime() <= previous || !frame.map(QVideoFrame::ReadOnly)) {
            qCritical() << "Frame contract:" << frame.size() << frame.pixelFormat() << frame.startTime();
            finish(3, "frame format/timestamp/map");
            return;
        }
        bool valid = frame.planeCount() == 3;
        int offset = frames * frameBytes;
        for (int plane = 0; valid && plane < 3; ++plane) {
            const int side = plane == 0 ? 64 : 32;
            const int stride = frame.bytesPerLine(plane);
            const auto *pixels = frame.bits(plane);
            valid = pixels && stride >= side && frame.mappedBytes(plane) >= stride * (side - 1) + side;
            for (int row = 0; valid && row < side; ++row) {
                valid = std::memcmp(pixels + row * stride, expected.constData() + offset, side) == 0;
                offset += side;
            }
        }
        previous = frame.startTime();
        frame.unmap();
        if (!valid) {
            finish(3, "decoded pixels differ");
            return;
        }
        ++frames;
        std::printf("frame=%d timestamp=%lld bytes=%d\n", frames, static_cast<long long>(previous), frameBytes);
    });
    QObject::connect(&player, &QMediaPlayer::errorOccurred, &app,
        [&](QMediaPlayer::Error error, const QString &message) {
            qInfo() << "Player error:" << error << message;
            finish(missing && frames == 0 && error != QMediaPlayer::NoError ? 0 : 4,
                   missing ? "missing media refused" : "unexpected playback error");
        });
    QObject::connect(&player, &QMediaPlayer::mediaStatusChanged, &app,
        [&](QMediaPlayer::MediaStatus status) {
            if (status == QMediaPlayer::EndOfMedia)
                finish(!missing && frames == 4 ? 0 : 3, "end of media and exact decoded pixels");
        });
    player.setVideoSink(&sink);
    QTimer::singleShot(15000, &app, [&] { finish(5, "playback timeout"); });
    QTimer::singleShot(0, &app, [&] {
        player.setSource(QUrl::fromLocalFile(args[1]));
        player.play();
    });
    const int status = app.exec();
    player.stop();
    return status;
}
