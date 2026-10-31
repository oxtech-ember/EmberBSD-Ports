// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).

#include "qbsdfbinputfailure_p.h"

#include <QByteArray>
#include <QCoreApplication>
#include <QMetaObject>
#include <QSocketNotifier>
#include <QTimer>

#include <cstdlib>
#include <iostream>
#include <unistd.h>

namespace {

struct InputCleanup {
    QTimer &pointerInput;
    QMetaObject::Connection pointerConnection;
    QSocketNotifier &notifier;
    bool pointerDisconnected = false;
    bool notifierDisabled = false;

    void operator()()
    {
        pointerInput.stop();
        pointerDisconnected = QObject::disconnect(pointerConnection);
        notifier.setEnabled(false);
        notifierDisabled = !notifier.isEnabled();
    }
};

int failureCase(QCoreApplication &application)
{
    int descriptors[2];
    if (::pipe(descriptors) == -1) {
        std::cerr << "FAIL: cannot create test notifier pipe\n";
        return 1;
    }
    QTimer pointerInput;
    QSocketNotifier notifier(descriptors[0], QSocketNotifier::Read, &application);
    int pointerEvents = 0;
    const QMetaObject::Connection pointerConnection = QObject::connect(
        &pointerInput, &QTimer::timeout, &application, [&] { ++pointerEvents; });
    InputCleanup cleanup{pointerInput, pointerConnection, notifier};
    pointerInput.start(1);
    notifier.setEnabled(true);
    bool callbackReturned = false;
    bool watchdogFired = false;
    bool cleanupAtAboutToQuit = false;
    QObject::connect(&application, &QCoreApplication::aboutToQuit, &application, [&] {
        cleanupAtAboutToQuit = cleanup.pointerDisconnected && cleanup.notifierDisabled
            && !pointerInput.isActive();
    });
    QTimer::singleShot(0, &application, [&] {
        QBsdFb::quitAfterInputFailure(cleanup);
        callbackReturned = true;
    });
    QTimer::singleShot(250, &application, [&] {
        watchdogFired = true;
        application.exit(99);
    });

    const int result = application.exec();
    if (result != EXIT_FAILURE || watchdogFired) {
        std::cerr << "FAIL: input failure exits with EXIT_FAILURE, got " << result << '\n';
        ::close(descriptors[0]);
        ::close(descriptors[1]);
        return 1;
    }
    if (!cleanup.pointerDisconnected || !cleanup.notifierDisabled
        || pointerInput.isActive() || pointerEvents != 0 || !callbackReturned
        || !cleanupAtAboutToQuit) {
        std::cerr << "FAIL: input cleanup completes in order before event-loop exit\n";
        ::close(descriptors[0]);
        ::close(descriptors[1]);
        return 1;
    }
    ::close(descriptors[0]);
    ::close(descriptors[1]);
    return 0;
}

int normalCleanupCase(QCoreApplication &application)
{
    int descriptors[2];
    if (::pipe(descriptors) == -1) {
        std::cerr << "FAIL: cannot create test notifier pipe\n";
        return 1;
    }
    QTimer pointerInput;
    QSocketNotifier notifier(descriptors[0], QSocketNotifier::Read, &application);
    int pointerEvents = 0;
    const QMetaObject::Connection pointerConnection = QObject::connect(
        &pointerInput, &QTimer::timeout, &application, [&] { ++pointerEvents; });
    InputCleanup cleanup{pointerInput, pointerConnection, notifier};
    pointerInput.start(1);
    notifier.setEnabled(true);
    bool secondEventRan = false;
    QTimer::singleShot(0, &application, [&] { cleanup(); });
    QTimer::singleShot(10, &application, [&] {
        secondEventRan = true;
        application.exit(0);
    });

    const int result = application.exec();
    if (result != 0 || !secondEventRan || !cleanup.pointerDisconnected
        || !cleanup.notifierDisabled || pointerInput.isActive() || pointerEvents != 0) {
        std::cerr << "FAIL: normal cleanup leaves the event loop running\n";
        ::close(descriptors[0]);
        ::close(descriptors[1]);
        return 1;
    }
    ::close(descriptors[0]);
    ::close(descriptors[1]);
    return 0;
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication application(argc, argv);
    if (argc != 2) {
        std::cerr << "usage: qt-bsdfb-inputfailure-test failure|normal\n";
        return 2;
    }
    const QByteArray mode(argv[1]);
    if (mode == "failure")
        return failureCase(application);
    if (mode == "normal")
        return normalCleanupCase(application);
    return 2;
}
