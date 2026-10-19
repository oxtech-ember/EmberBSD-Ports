// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
#include <kdirwatch.h>
#include <kdirwatch_p.h>
#include <QCoreApplication>
#include <QFile>
#include <QMetaObject>
#include <QTemporaryDir>
#include <cstdio>
#include <cstdlib>

#define CHECK(condition) do { if (!(condition)) { \
    std::fprintf(stderr, "CHECK failed: %s at %s:%d\n", #condition, __FILE__, __LINE__); \
    std::abort(); } } while (false)

class KDirWatch_UnitTest
{
public:
    static const KDirWatchPrivate::Entry &entry(KDirWatchPrivate *state, const QString &path)
    {
        auto found = state->m_mapEntries.constFind(path);
        CHECK(found != state->m_mapEntries.cend());
        return found.value();
    }

    static void event(KDirWatchPrivate *state, const QString &path)
    {
        CHECK(QMetaObject::invokeMethod(state, "fswEventReceived", Qt::DirectConnection, Q_ARG(QString, path)));
    }

    static void createdChildren(bool keepParent)
    {
        QTemporaryDir temporary;
        CHECK(temporary.isValid());
        const QString parent = temporary.path();
        KDirWatch watch;
        if (keepParent) {
            watch.addDir(parent);
        }
        QStringList paths;
        for (int i = 0; i != 4; ++i) {
            paths.append(parent + QStringLiteral("/child-%1").arg(i));
            watch.addFile(paths.constLast());
        }
        KDirWatchPrivate *state = watch.d;
        CHECK(state != nullptr);
        CHECK(state->m_preferredMethod == KDirWatch::QFSWatch);
        CHECK(entry(state, parent).m_entries.size() == paths.size());
        for (const QString &path : paths) {
            CHECK(entry(state, path).m_status == KDirWatchPrivate::NonExistent);
            QFile file(path);
            CHECK(file.open(QIODevice::WriteOnly));
            CHECK(file.write("x", 1) == 1);
        }
        event(state, parent);
        for (const QString &path : paths) {
            auto child = state->m_mapEntries.constFind(path);
            CHECK(child != state->m_mapEntries.cend());
            CHECK(child->m_status == KDirWatchPrivate::Normal);
            CHECK(child->m_clients.size() == 1);
            CHECK(child->m_clients.front().count == 1);
        }
        const auto parentEntry = state->m_mapEntries.constFind(parent);
        if (keepParent) {
            CHECK(parentEntry != state->m_mapEntries.cend());
            CHECK(parentEntry->m_entries.isEmpty());
        } else {
            CHECK(parentEntry == state->m_mapEntries.cend());
        }
    }

    static void repeatedMissing()
    {
        QTemporaryDir temporary;
        CHECK(temporary.isValid());
        const QString parent = temporary.path();
        const QString path = parent + QStringLiteral("/missing");
        KDirWatch watch;
        watch.addFile(path);
        KDirWatchPrivate *state = watch.d;
        CHECK(state != nullptr);
        CHECK(entry(state, parent).m_entries.size() == 1);
        for (int i = 0; i != 8; ++i) {
            event(state, path);
            CHECK(entry(state, path).m_status == KDirWatchPrivate::NonExistent);
            CHECK(entry(state, parent).m_entries.size() == 1);
            CHECK(entry(state, path).m_clients.size() == 1);
            CHECK(entry(state, path).m_clients.front().count == 1);
        }
    }
};

int main(int argc, char **argv)
{
    QCoreApplication application(argc, argv);
    CHECK(argc == 2);
    const QByteArray mode(argv[1]);
    if (mode == "children") {
        KDirWatch_UnitTest::createdChildren(true);
    } else if (mode == "parent-removal") {
        KDirWatch_UnitTest::createdChildren(false);
    } else if (mode == "missing") {
        KDirWatch_UnitTest::repeatedMissing();
    } else {
        CHECK(false);
    }
    QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
    std::puts("KDirWatch real entry contract PASS");
    return 0;
}
