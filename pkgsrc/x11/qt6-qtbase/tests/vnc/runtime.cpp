// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <QGuiApplication>
#include <QScreen>
#include <QTimer>
#include <cstdio>

int main(int argc, char **argv)
{
    QGuiApplication application(argc, argv);
    if (QGuiApplication::platformName() != QStringLiteral("vnc")
            || QGuiApplication::screens().size() != 1)
        return 2;
    const QScreen *screen = QGuiApplication::primaryScreen();
    if (!screen || screen->size() != QSize(160, 128))
        return 2;
    std::printf("Qt=%s platform=vnc screens=1 width=%d height=%d\n",
                qVersion(), screen->size().width(), screen->size().height());
    QTimer::singleShot(50, &application, &QGuiApplication::quit);
    return application.exec();
}
