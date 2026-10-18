// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
#include <QtCore/QAbstractEventDispatcher>
#include <QtCore/QCoreApplication>
#include <QtCore/QElapsedTimer>
#include <QtCore/QProcess>
#include <QtCore/QThread>
#include <QtCore/QTimer>
#include <QtGui/QGuiApplication>
#include <cstdio>
#include <cstring>
#include <memory>

int main(int argc, char **argv)
{
    bool gui = false;
    bool threadFirst = false;
    bool missing = false;
    bool detachedFirst = false;
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--gui") == 0)
            gui = true;
        else if (std::strcmp(argv[i], "--thread-first") == 0)
            threadFirst = true;
        else if (std::strcmp(argv[i], "--detached-first") == 0)
            detachedFirst = true;
        else if (std::strcmp(argv[i], "--missing") == 0)
            missing = true;
        else {
            std::fprintf(stderr, "Usage: %s [--gui] [--thread-first] [--detached-first] [--missing]\n", argv[0]);
            return 64;
        }
    }
    std::unique_ptr<QCoreApplication> app;
    if (gui)
        app = std::make_unique<QGuiApplication>(argc, argv);
    else
        app = std::make_unique<QCoreApplication>(argc, argv);
    std::printf("dispatcher=%s\n", QAbstractEventDispatcher::instance()->metaObject()->className());
    std::unique_ptr<QThread> thread;
    if (threadFirst) {
        thread.reset(QThread::create([] {}));
        thread->start();
        if (!thread->wait(5000)) {
            std::fprintf(stderr, "FAIL: thread did not finish\n");
            return 4;
        }
    }
    if (detachedFirst && !QProcess::startDetached(QStringLiteral("/bin/sh"),
            {QStringLiteral("-c"), QStringLiteral("exit 0")})) {
        std::fprintf(stderr, "FAIL: detached child did not start\n");
        return 5;
    }
    QProcess process;
    QElapsedTimer elapsed;
    QTimer deadline;
    deadline.setSingleShot(true);
    int started = 0;
    int finished = 0;
    const int iterations = missing ? 1 : 20;
    const auto start = [&] {
        deadline.start(5000);
        // /dev/null is a file. A child path must fail even if a test name exists.
        if (missing)
            process.start(QStringLiteral("/dev/null/ember-qt-process-missing"));
        else
            process.start(QStringLiteral("/bin/sh"), {QStringLiteral("-c"), QStringLiteral("exit 0")});
    };
    QObject::connect(&process, &QProcess::started, &deadline, [&] {
        ++started;
        std::printf("started=%d pid=%lld elapsed_ms=%lld\n", started,
                    static_cast<long long>(process.processId()), static_cast<long long>(elapsed.elapsed()));
        std::fflush(stdout);
    });
    QObject::connect(&process, &QProcess::finished, &deadline, [&](int status, QProcess::ExitStatus kind) {
        deadline.stop();
        if (missing || status != 0 || kind != QProcess::NormalExit || ++finished != started) {
            std::fprintf(stderr, "FAIL: child status=%d kind=%d started=%d finished=%d\n",
                         status, int(kind), started, finished);
            app->exit(1);
        } else if (finished == iterations) {
            std::printf("PASS: %d asynchronous child exits elapsed_ms=%lld\n", finished,
                        static_cast<long long>(elapsed.elapsed()));
            app->exit(0);
        } else {
            QTimer::singleShot(0, app.get(), start);
        }
    });
    QObject::connect(&process, &QProcess::errorOccurred, &deadline, [&](QProcess::ProcessError error) {
        deadline.stop();
        if (missing && error == QProcess::FailedToStart && started == 0) {
            std::puts("PASS: missing executable reported FailedToStart");
            app->exit(3);
        } else {
            std::fprintf(stderr, "FAIL: error=%d message=%s\n", int(error), qPrintable(process.errorString()));
            app->exit(1);
        }
    });
    QObject::connect(&deadline, &QTimer::timeout, [&] {
        std::fprintf(stderr, "FAIL: timeout state=%d started=%d finished=%d elapsed_ms=%lld\n",
                     int(process.state()), started, finished, static_cast<long long>(elapsed.elapsed()));
        process.kill();
        process.waitForFinished(1000);
        app->exit(2);
    });
    elapsed.start();
    // Start after exec() so synchronous launch errors also terminate the loop.
    QTimer::singleShot(0, app.get(), start);
    return app->exec();
}
