// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Installed Qt package consumer, not a GPU test.
#include <QBuffer>
#include <QCoreApplication>
#include <QDebug>
#include <QEventLoop>
#include <QFile>
#include <QImage>
#include <QImageReader>
#include <QLibraryInfo>
#include <QPainter>
#include <QObject>
#include <QSvgRenderer>
#include <QThread>
#include <QTimer>
#include <memory>
#include <cstdio>
#include <link_elf.h>

class Emitter : public QObject
{
    Q_OBJECT
signals:
    void computed(quint64 value);
};

static bool pixels(const QImage &image)
{
    return image.size() == QSize(64, 64)
        && image.pixelColor(32, 32) == QColor(224, 48, 32)
        && image.pixelColor(2, 2).alpha() == 0;
}

static int loadedLibrary(dl_phdr_info *info, size_t, void *)
{
    if (info->dlpi_name && *info->dlpi_name)
        std::printf("loaded=%s\n", info->dlpi_name);
    return 0;
}

int main(int argc, char **argv)

{
    QCoreApplication app(argc, argv);
    if (app.arguments().contains(QStringLiteral("--no-plugins")))
        QCoreApplication::setLibraryPaths({});
    qInfo().noquote() << "Qt" << qVersion() << "plugins"
                     << QLibraryInfo::path(QLibraryInfo::PluginsPath);
    if (QString::fromLatin1(qVersion()) != QStringLiteral("6.12.0"))
        return 1;
    QFile resource(QStringLiteral(":/ember-check/fixture.svg"));
    if (!resource.open(QIODevice::ReadOnly))
        return 2;
    const QByteArray svg = resource.readAll();
    const auto formats = QImageReader::supportedImageFormats();
    qInfo() << "image formats" << formats;
    for (const auto &format : {QByteArray("svg"), QByteArray("png"),
                               QByteArray("jp2"), QByteArray("mng")}) {
        if (!formats.contains(format)) {
            qCritical() << "Missing image plugin" << format;
            return 3;
        }
    }
    for (int cycle = 0; cycle < 4; ++cycle) {
        Emitter emitter;
        QEventLoop loop;
        QTimer deadline;
        deadline.setSingleShot(true);
        bool received = false;
        const quint64 expected = quint64(cycle + 1) * 500500;
        QObject::connect(&emitter, &Emitter::computed, &loop,
            [&](quint64 value) {
                received = value == expected && QThread::currentThread() == app.thread();
                loop.quit();
            }, Qt::QueuedConnection);
        QObject::connect(&deadline, &QTimer::timeout, &loop, &QEventLoop::quit);
        std::unique_ptr<QThread> worker(QThread::create([&emitter, cycle] {
            quint64 value = 0;
            for (quint64 i = 1; i <= 1000; ++i)
                value += i * quint64(cycle + 1);
            emit emitter.computed(value);
        }));
        deadline.start(5000);
        worker->start();
        loop.exec();
        // Never destroy a still-running QThread on an error path.
        if (!worker->wait(5000))
            qFatal("Worker failed to finish");
        if (!received)
            return 4;
        QSvgRenderer renderer(svg);
        if (!renderer.isValid())
            return 5;
        QImage painted(64, 64, QImage::Format_ARGB32_Premultiplied);
        painted.fill(Qt::transparent);
        {
            QPainter painter(&painted);
            renderer.render(&painter);
        }
        if (!pixels(painted))
            return 6;
        QImageReader svgReader(QStringLiteral(":/ember-check/fixture.svg"));
        if (!pixels(svgReader.read()))
            return 7;
        QByteArray encoded;
        QBuffer output(&encoded);
        if (!output.open(QIODevice::WriteOnly) || !painted.save(&output, "PNG"))
            return 8;
        output.close();
        if (!pixels(QImage::fromData(encoded, "PNG")))
            return 9;
        QSvgRenderer invalid(QByteArray("<svg><broken>"));
        if (invalid.isValid() || !QImage::fromData(QByteArray("invalid"), "PNG").isNull())
            return 10;
        QImageReader missing(QStringLiteral(":/ember-check/missing.svg"));
        if (!missing.read().isNull())
            return 11;
        qInfo() << "PASS cycle" << cycle + 1 << "queued signal, resource, SVG pixels, PNG and invalid inputs";
    }
    return dl_iterate_phdr(loadedLibrary, nullptr) == 0 ? 0 : 12;
}
#include "main.moc"
