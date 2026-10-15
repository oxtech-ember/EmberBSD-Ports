// SPDX-License-Identifier: BSD-2-Clause
// Public ABI consumer. Run against both the accepted nb2 and candidate nb3 libraries.
#include <KDirWatch>
#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QFile>
#include <QStringList>
#include <QTemporaryDir>
#include <QThread>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <functional>
#include <stdexcept>
#include <sys/resource.h>
#include <sys/time.h>
#include <fcntl.h>
#include <unistd.h>

static void require(bool value, const char *message)
{
    if (!value) {
        throw std::runtime_error(message);
    }
}

static void writeFile(const QString &path, const QByteArray &value)
{
    QFile file(path);
    require(file.open(QIODevice::WriteOnly | QIODevice::Truncate), "fixture file open failed");
    require(file.write(value) == value.size() && file.flush(), "fixture file write failed");
}

static void changeTime(const QString &path, int sequence)
{
    // Stat uses second-resolution ctime/mtime. Set an increasing fixture mtime.
    timeval times[2] = {};
    times[0].tv_sec = times[1].tv_sec = QDateTime::currentSecsSinceEpoch() + 60 + sequence;
    require(utimes(QFile::encodeName(path).constData(), times) == 0, "fixture timestamp update failed");
}

static int descriptorCount(rlim_t ceiling)
{
    int count = 0;
    for (rlim_t fd = 0; fd < ceiling; ++fd) {
        errno = 0;
        if (fcntl(int(fd), F_GETFD) != -1) {
            ++count;
        } else {
            require(errno == EBADF, "descriptor enumeration failed");
        }
    }
    return count;
}

static void awaitEvent(const std::function<bool()> &predicate, const char *message)
{
    QElapsedTimer timer;
    timer.start();
    while (!predicate() && timer.elapsed() < 8000) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 20);
        QThread::msleep(10);
    }
    require(predicate(), message);
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    if (argc != 2) {
        std::fprintf(stderr, "Usage: %s EXISTING_OUTPUT_DIRECTORY\n", argv[0]);
        return 2;
    }
    try {
        rlimit limit;
        require(getrlimit(RLIMIT_NOFILE, &limit) == 0, "getrlimit failed");
        if (limit.rlim_max != RLIM_INFINITY && limit.rlim_max < 1024) {
            std::fprintf(stderr, "SKIP: hard descriptor limit is below 1024\n");
            return 77;
        }
        limit.rlim_cur = 1024;
        require(setrlimit(RLIMIT_NOFILE, &limit) == 0, "setrlimit failed");
        require(getrlimit(RLIMIT_NOFILE, &limit) == 0 && limit.rlim_cur == 1024,
                "soft descriptor limit was not set to 1024");
        if (limit.rlim_max == RLIM_INFINITY || limit.rlim_max > 65536) {
            std::fprintf(stderr, "SKIP: fixture requires a finite hard descriptor limit at most 65536\n");
            return 77;
        }
        const QString output = QString::fromLocal8Bit(argv[1]);
        require(QDir(output).exists(), "output directory does not exist");
        QTemporaryDir fixture(QDir(output).filePath(QStringLiteral("kdirwatch-tree-XXXXXX")));
        require(fixture.isValid(), "new fixture directory failed");
        QStringList directories, files;
        for (int index = 0; index < 600; ++index) {
            const QString directory = fixture.path() + QStringLiteral("/head-%1").arg(index, 4, 10, QLatin1Char('0'));
            require(QDir().mkpath(directory), "fixture directory creation failed");
            directories.append(directory);
            files.append(directory + QStringLiteral("/value"));
            writeFile(files.last(), "head\n");
        }
        const QString polling = fixture.path() + QStringLiteral("/polling");
        const QString nested = polling + QStringLiteral("/nested/deeper");
        const QString value = nested + QStringLiteral("/value");
        const QString moved = nested + QStringLiteral("/renamed");
        require(QDir().mkpath(nested), "polling tree creation failed");
        writeFile(value, "initial\n");
        changeTime(value, 0);
        QCoreApplication::processEvents();
        const int before = descriptorCount(limit.rlim_max);
        {
            KDirWatch watcher;
            require(watcher.internalMethod() == KDirWatch::QFSWatch, "default backend is not QFSWatch");
            QStringList dirty, created, deleted;
            QObject::connect(&watcher, &KDirWatch::dirty, &app, [&](const QString &path) { dirty.append(path); });
            QObject::connect(&watcher, &KDirWatch::created, &app, [&](const QString &path) { created.append(path); });
            QObject::connect(&watcher, &KDirWatch::deleted, &app, [&](const QString &path) { deleted.append(path); });
            for (int index = 0; index < directories.size(); ++index) {
                watcher.addDir(directories[index]);
                watcher.addFile(files[index]);
            }
            QCoreApplication::processEvents();
            const int peak = descriptorCount(limit.rlim_max);
            std::printf("FD before=%d peak=%d soft=1024 paths=1200\n", before, peak);
            std::fflush(stdout);
            require(peak - before <= 512 + 16 && peak < 768, "native watch FD budget exceeded");
            watcher.addDir(polling, KDirWatch::WatchFiles | KDirWatch::WatchSubDirs);
            require(watcher.contains(value), "recursive registration did not include the existing nested file");
            const QString reserve = fixture.path() + QStringLiteral("/ordinary-file-reserve");
            writeFile(reserve, "descriptor reserve works\n");
            dirty.clear();
            writeFile(value, "changed nested content\n");
            changeTime(value, 1);
            awaitEvent([&] { return dirty.contains(value); }, "polling nested-file change timed out");
            deleted.clear();
            require(QFile::rename(value, moved), "fixture rename failed");
            changeTime(nested, 2);
            awaitEvent([&] { return deleted.contains(value); }, "polling rename notification timed out");
            created.clear();
            writeFile(value, "recreated after rename\n");
            changeTime(value, 3);
            awaitEvent([&] { return created.contains(value); }, "polling recreation after rename timed out");
            deleted.clear();
            require(QFile::remove(value), "fixture deletion failed");
            changeTime(nested, 4);
            awaitEvent([&] { return deleted.contains(value); }, "polling deletion timed out");
            created.clear();
            writeFile(value, "recreated after deletion\n");
            changeTime(value, 5);
            awaitEvent([&] { return created.contains(value); }, "polling recreation after deletion timed out");
            dirty.clear();
            writeFile(value, "changed again after two recreations\n");
            changeTime(value, 6);
            awaitEvent([&] { return dirty.contains(value); }, "polling change after recreation timed out");
            const int repeated = descriptorCount(limit.rlim_max);
            std::printf("FD after polling lifecycle=%d\n", repeated);
            require(repeated <= peak + 4, "repeated polling events grew native descriptors");
        }
        QCoreApplication::processEvents();
        const int after = descriptorCount(limit.rlim_max);
        std::printf("FD after watcher destruction=%d\n", after);
        require(after <= before + 4, "watcher destruction retained path descriptors");
        require(fixture.remove(), "fixture cleanup failed");
        std::puts("PASS: bounded native descriptors, recursive polling changes, rename/delete/recreate and cleanup");
        return 0;
    } catch (const std::exception &error) {
        std::fprintf(stderr, "FAIL: %s\n", error.what());
        return 1;
    }
}
