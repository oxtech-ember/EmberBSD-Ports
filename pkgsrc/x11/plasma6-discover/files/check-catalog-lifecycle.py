#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.

"""Exercise the production Discover catalog methods with real Qt Core processes.

The fixture substitutes the executable paths, exposes the backend state and
provides minimal Discover resource and stream types. It installs no packages
and uses neither a live SDK configuration nor D-Bus.
"""

import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).with_name("EmberBSDBackend") / "EmberBSDBackend.cpp"

CMAKE = """
cmake_minimum_required(VERSION 3.20)
project(CatalogLifecycle LANGUAGES CXX)
find_package(Qt6 REQUIRED COMPONENTS Core)
add_executable(check-catalog main.cpp)
target_compile_features(check-catalog PRIVATE cxx_std_20)
target_compile_definitions(check-catalog PRIVATE QT_USE_QSTRINGBUILDER)
target_link_libraries(check-catalog PRIVATE Qt6::Core)
set_target_properties(check-catalog PROPERTIES BUILD_RPATH "$<TARGET_FILE_DIR:Qt6::Core>")
"""

CLIENT = """#!/bin/sh
[ "$#" -eq 1 ] && [ "$1" = catalog ] || exit 64
case "$EMBER_DISCOVER_TEST_CASE" in
hang) exec /bin/sleep 10 ;;
error) echo 'Catalog fixture error' >&2; exit 7 ;;
slow-ok) /bin/sleep 0.05 ;;
esac
echo '{"schema":"emberbsd.catalog-index.v1","release_id":"fixture","desktop_binding":"unavailable","counts":{"total":1},"packages":[{"base":"curl","version":"8.23.0","pkgname":"curl-8.23.0"}]}'
"""

STUBS = r"""
#include <QCoreApplication>
#include <QElapsedTimer>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
#include <QProcess>
#include <QString>
#include <QThread>
#include <QTimer>
#include <QVector>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <utility>

static QString client;
static QString config;
// Use a short timeout while keeping the production QTimer call unchanged.
int catalogTimeoutMs = 2000;

QString i18n(const char *message) { return QString::fromUtf8(message); }

struct Filters {};
using StreamResult = int;
class ResultsStream : public QObject {
public:
    int deliveries = 0;
    qsizetype results = 0;

    void deliver(const QVector<StreamResult> &items)
    {
        ++deliveries;
        results = items.size();
    }
};
using EmberBSDResultsStream = ResultsStream;

class EmberBSDResource : public QObject {
public:
    EmberBSDResource(const QJsonObject &, const QJsonObject &, const QString &, QObject *parent)
        : QObject(parent)
    {}
    bool isDesktop() const { return false; }
};

class EmberBSDBackend : public QObject {
public:
    struct PendingSearch {
        QPointer<EmberBSDResultsStream> stream;
        Filters filter;
    };
    void reload();
    // APPLY_CATALOG_DECLARATION
    void completePending();
    ResultsStream *searchCatalog(const Filters &);
    QVector<StreamResult> match(const Filters &) const { return QVector<StreamResult>(m_resources.size()); }
    void passiveMessage(const QString &) { ++errors; }
    void fetchingUpdatesProgressChanged() {}
    void contentsChanged()
    {
        ++completions;
        if (completed)
            completed();
    }
    void resourceRemoved(EmberBSDResource *) {}

    QVector<EmberBSDResource *> m_resources;
    QVector<PendingSearch> m_pending;
    QProcess *m_process = nullptr;
    QString m_error;
    QString m_binding;
    bool m_ready = false;
    int m_desktopCount = 0;
    int completions = 0;
    int errors = 0;
    std::function<void()> completed;
};
"""

MAIN = r"""
static void require(bool condition, const char *message)
{
    if (!condition) {
        std::fprintf(stderr, "%s\n", message);
        std::exit(1);
    }
}

static void pumpUntil(const std::function<bool()> &done)
{
    QElapsedTimer timer;
    timer.start();
    while (!done() && timer.elapsed() < 4000) {
        QCoreApplication::processEvents();
        QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
        QThread::msleep(1);
    }
}

static void checkRequest(EmberBSDBackend &backend, int generation, bool success)
{
    const int errors = backend.errors;
    catalogTimeoutMs = config == QStringLiteral("hang") ? 150 : 2000;
    backend.reload();
    const QPointer<QProcess> first = backend.m_process;
    backend.reload();
    require(first == backend.m_process, "second reload replaced the in-flight process");
    auto one = QPointer<ResultsStream>(backend.searchCatalog(Filters{}));
    auto two = QPointer<ResultsStream>(backend.searchCatalog(Filters{}));
    delete backend.searchCatalog(Filters{}); // Closing a search must not strand pending work.
    pumpUntil([&] { return !first && backend.completions == generation; });
    require(backend.m_ready, "backend did not become ready");
    require(!backend.m_process, "in-flight process was not released");
    require(!first, "retired child was not deleted");
    require(backend.m_pending.empty(), "pending searches were not released");
    require(backend.completions == generation, "catalog completed more or less than once");
    require(one->deliveries == 1 && two->deliveries == 1, "pending search completion was not unique");
    require(one->results == (success ? 1 : 0) && two->results == one->results,
            "pending search got unexpected results");
    require(backend.m_error.isEmpty() == success, "unexpected catalog error state");
    require(backend.errors == errors + (success ? 0 : 1), "unexpected error emission count");
    delete one;
    delete two;
}

static void reloadDuringTimeoutCompletion()
{
    EmberBSDBackend backend;
    config = QStringLiteral("hang");
    catalogTimeoutMs = 150;
    qputenv("EMBER_DISCOVER_TEST_CASE", config.toUtf8());
    backend.reload();
    const QPointer<QProcess> retired = backend.m_process;
    const QPointer<ResultsStream> expired = backend.searchCatalog(Filters{});
    QPointer<ResultsStream> next;
    QPointer<QProcess> replacement;
    bool lateFinishedDuringReload = false;
    QObject::connect(retired, &QProcess::finished, &backend, [&] {
        lateFinishedDuringReload = replacement && backend.m_process == replacement;
    });
    backend.completed = [&] {
        if (backend.completions != 1)
            return;
        require(backend.m_error.contains(QStringLiteral("timed out")),
                "timeout did not report its diagnostic");
        require(expired->deliveries == 1 && expired->results == 0,
                "timed-out pending search did not finish once");
        config = QStringLiteral("slow-ok");
        catalogTimeoutMs = 2000;
        qputenv("EMBER_DISCOVER_TEST_CASE", config.toUtf8());
        backend.reload();
        replacement = backend.m_process;
        require(replacement && replacement != retired, "timeout completion could not start reload");
        next = backend.searchCatalog(Filters{});
    };
    pumpUntil([&] { return backend.completions == 2 && !retired && !replacement; });
    require(lateFinishedDuringReload, "old finished signal did not reach the active reload");
    require(!retired && !replacement, "one of the two processes was not reaped");
    require(backend.completions == 2 && backend.errors == 1 && backend.m_ready,
            "late finished signal disturbed the current catalog read");
    require(expired->deliveries == 1 && next && next->deliveries == 1 && next->results == 1,
            "late finished signal lost or duplicated a pending result");
    delete expired;
    delete next;
}


int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    require(argc == 3, "expected fixture client and case");
    client = QString::fromLocal8Bit(argv[1]);
    config = QString::fromLocal8Bit(argv[2]);
    qputenv("EMBER_DISCOVER_TEST_CASE", config.toUtf8());
    if (config == QStringLiteral("late-finished")) {
        reloadDuringTimeoutCompletion();
        return 0;
    }
    const QString originalClient = client;
    if (config == QStringLiteral("missing"))
        client = originalClient + QStringLiteral(".not-found");
    EmberBSDBackend backend;
    checkRequest(backend, 1, config == QStringLiteral("ok"));
    if (config == QStringLiteral("error"))
        require(backend.m_error == QStringLiteral("Catalog fixture error"), "child stderr lost");
    client = originalClient;
    config = QStringLiteral("ok");
    qputenv("EMBER_DISCOVER_TEST_CASE", config.toUtf8());
    checkRequest(backend, 2, true);
    return 0;
}
"""


def method(source, name):
    start = re.search(rf"(?m)^.*\bEmberBSDBackend::{name}\(", source).start()
    opening = source.index("{", start)
    depth = 0
    for pos in range(opening, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise ValueError(f"Unclosed method: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qt-prefix", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=SOURCE)
    args = parser.parse_args()
    source = args.source.read_text()
    apply_catalog = method(source, "applyCatalog")
    signature = apply_catalog[:apply_catalog.index("{")].strip()
    stubs = STUBS.replace("// APPLY_CATALOG_DECLARATION", signature.replace("EmberBSDBackend::", "") + ";")
    methods = "\n\n".join((method(source, "reload"), apply_catalog,
                           method(source, "completePending"), method(source, "searchCatalog")))
    with tempfile.TemporaryDirectory(prefix="ember-discover-catalog-") as temp:
        root = Path(temp)
        (root / "main.cpp").write_text(stubs + methods + MAIN)
        (root / "CMakeLists.txt").write_text(CMAKE)
        fixture = root / "ember-update"
        fixture.write_text(CLIENT)
        fixture.chmod(0o755)
        build = root / "build"
        qt_config = args.qt_prefix / "lib" / "cmake" / "Qt6"
        if not (qt_config / "Qt6Config.cmake").is_file():
            parser.error("--qt-prefix must point to a native Qt SDK")
        qt_options = ["-DCMAKE_PREFIX_PATH=" + str(args.qt_prefix), "-DQt6_DIR=" + str(qt_config)]
        subprocess.run(["cmake", "-S", str(root), "-B", str(build), *qt_options],
                       check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["cmake", "--build", str(build)], check=True,
                       stdout=subprocess.DEVNULL)
        failed = False
        for case in ("ok", "missing", "error", "hang", "late-finished"):
            result = subprocess.run([build / "check-catalog", fixture, case],
                                    capture_output=True, text=True, timeout=8)
            if result.returncode:
                print(f"FAIL: {case}: {result.stderr.strip()}", file=sys.stderr)
                failed = True
            else:
                print(f"PASS: {case}, pending search completion and next reload")
        return int(failed)


if __name__ == "__main__":
    sys.exit(main())
