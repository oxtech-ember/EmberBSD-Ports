// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Compiled QML module with real V3D scene graph.
#include <QDebug>
#include <QGuiApplication>
#include <QImage>
#include <QOpenGLContext>
#include <QOpenGLFunctions>
#include <QQuickItem>
#include <QQuickView>
#include <QSGRendererInterface>
#include <QSurfaceFormat>
#include <QTimer>
#include <array>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <link_elf.h>

static int loadedLibrary(dl_phdr_info *info, size_t, void *)
{
    if (info->dlpi_name && *info->dlpi_name)
        std::printf("loaded=%s\n", info->dlpi_name);
    return 0;
}

int main(int argc, char **argv)
{
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    QSurfaceFormat format;
    format.setRenderableType(QSurfaceFormat::OpenGLES);
    format.setVersion(3, 0);
    QSurfaceFormat::setDefaultFormat(format);
    QQuickWindow::setGraphicsApi(QSGRendererInterface::OpenGL);
    QGuiApplication app(argc, argv);
    if (QGuiApplication::platformName() != QStringLiteral("wayland")) {
        qCritical() << "FAIL: actual Wayland QPA required";
        return 2;
    }
    const bool wrongPixel = app.arguments().contains(QStringLiteral("--wrong-pixel"));
    const bool missingModule = app.arguments().contains(QStringLiteral("--missing-module"));
    std::atomic<int> renderer{0};
    unsigned phase = 0;
    int status;
    {
        bool pending = false;
        QQuickView view;
        view.setTitle(QStringLiteral("EmberBSD Qt Quick V3D check"));
        QObject::connect(&view, &QQuickWindow::beforeRendering, &view, [&] {
            if (renderer.load() != 0)
                return;
            auto *context = QOpenGLContext::currentContext();
            auto *egl = context ? context->nativeInterface<QNativeInterface::QEGLContext>() : nullptr;
            const char *name = context ? reinterpret_cast<const char *>(
                context->functions()->glGetString(GL_RENDERER)) : nullptr;
            const char *expected = std::getenv("EMBER_QTQUICK_EXPECTED_RENDERER");
            if (expected == nullptr || *expected == '\0')
                expected = "V3D ";
            const bool valid = view.rendererInterface()->graphicsApi() == QSGRendererInterface::OpenGL
                && egl && egl->display() && egl->nativeContext() && name
                && std::strncmp(name, expected, std::strlen(expected)) == 0;
            if (name)
                std::printf("renderer=%s\nQt=%s\n", name, qVersion());
            renderer.store(valid ? 1 : -1);
        }, Qt::DirectConnection);
        view.loadFromModule(missingModule ? "Ember.MissingGpuModule" : "Ember.GpuCheck", "Scene");
        if (view.status() != QQuickView::Ready || !view.rootObject()) {
            qCritical() << "FAIL: QML module load" << view.errors();
            return 2;
        }
        QObject::connect(&view, &QQuickWindow::frameSwapped, &view, [&] {
            if (pending || phase >= 16)
                return;
            pending = true;
            QTimer::singleShot(100, &view, [&] {
                if (renderer.load() != 1) {
                    qCritical() << "FAIL: Qt Quick did not use EGL/V3D";
                    app.exit(3);
                    return;
                }
                const QImage image = view.grabWindow();
                const std::array<QColor, 4> colors = {Qt::red, Qt::blue, Qt::magenta, Qt::cyan};
                const QColor expected = wrongPixel ? QColor(17, 17, 17) : colors[phase % 4];
                if (image.size() != QSize(640, 400)) {
                    qCritical() << "FAIL: Qt Quick image geometry" << image.size();
                    app.exit(3);
                    return;
                }
                for (int y = 0; y < 32; ++y) {
                    for (int x = 0; x < 32; ++x) {
                        if (image.pixelColor(304 + x, 184 + y) != expected
                            || image.pixelColor(32 + x, 32 + y) != QColor(Qt::green)) {
                            qCritical() << "FAIL: Qt Quick pixel mismatch";
                            app.exit(3);
                            return;
                        }
                    }
                }
                std::printf("phase=%u scene-pixels=1024 layer-pixels=1024\n", ++phase);
                if (phase == 16) {
                    dl_iterate_phdr(loadedLibrary, nullptr);
                    app.exit(0);
                    return;
                }
                if (!view.rootObject()->setProperty("phase", phase)) {
                    qCritical() << "FAIL: QML phase update";
                    app.exit(3);
                    return;
                }
                pending = false;
                view.requestUpdate();
            });
        });
        QTimer deadline;
        deadline.setSingleShot(true);
        QObject::connect(&deadline, &QTimer::timeout, &app, [&] {
            qCritical() << "FAIL: Qt Quick deadline";
            app.exit(4);
        });
        deadline.start(20000);
        view.show();
        status = app.exec();
    }
    if (status == 0 && phase == 16)
        std::puts("PASS: Qt Quick V3D QML scene/layer pixels and window destruction");
    else if (status == 0)
        status = 5;
    return status;
}
