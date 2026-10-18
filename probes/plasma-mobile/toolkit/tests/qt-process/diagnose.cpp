#include <QtCore/QAbstractEventDispatcher>
#include <QtGui/QGuiApplication>
#include <cstring>
#include <memory>
#include <QtCore/QCoreApplication>
#include <QtCore/QElapsedTimer>
#include <QtCore/QProcess>
#include <QtCore/QTimer>
#include <cstdio>
int main(int argc, char **argv)
{
    std::unique_ptr<QCoreApplication> app;
    if (argc == 2 && std::strcmp(argv[1], "--gui") == 0)
        app = std::make_unique<QGuiApplication>(argc, argv);
    else
        app = std::make_unique<QCoreApplication>(argc, argv);
    std::printf("dispatcher=%s\n", QAbstractEventDispatcher::instance()->metaObject()->className());
    QProcess process;
    QElapsedTimer elapsed;
    QTimer timeout;
    timeout.setSingleShot(true);
    QObject::connect(&process, &QProcess::started, [&] {
        std::printf("started pid=%lld elapsed_ms=%lld\n", (long long)process.processId(), (long long)elapsed.elapsed());
        std::fflush(stdout);
    });
    QObject::connect(&process, &QProcess::finished, [&](int status, QProcess::ExitStatus kind) {
        std::printf("finished status=%d kind=%d elapsed_ms=%lld\n", status, int(kind), (long long)elapsed.elapsed());
        app->exit(status == 0 && kind == QProcess::NormalExit ? 0 : 1);
    });
    QObject::connect(&timeout, &QTimer::timeout, [&] {
        std::fprintf(stderr, "timeout state=%d elapsed_ms=%lld\n", int(process.state()), (long long)elapsed.elapsed());
        process.kill();
        process.waitForFinished(1000);
        app->exit(2);
    });
    QObject::connect(&process, &QProcess::errorOccurred, [&](QProcess::ProcessError error) {
        std::fprintf(stderr, "error=%d message=%s\n", int(error), qPrintable(process.errorString()));
        app->exit(3);
    });
    elapsed.start();
    timeout.start(5000);
    process.start(QStringLiteral("/bin/sh"), {QStringLiteral("-c"), QStringLiteral("exit 0")});
    return app->exec();
}
