// SPDX-License-Identifier: BSD-2-Clause
// Run unchanged upstream method bodies. Only external watcher/timer boundaries
// are doubled; source extraction happens in the runner.
#include <QString>
#include <QStringList>
#include <QLoggingCategory>
#include <cstdio>
#include <cerrno>

#define HAVE_QFILESYSTEMWATCHER 1
#define HAVE_SYS_INOTIFY_H 1
Q_LOGGING_CATEGORY(KDIRWATCH, "ember.test.kdirwatch", QtWarningMsg)

class TestFileSystemWatcher {
public:
    bool succeeds = true;
    int adds = 0;
    QStringList watchedFiles, watchedDirs;
    bool addPath(const QString &path) {
        ++adds;
        if (!succeeds) { errno = EMFILE; return false; }
        watchedFiles.append(path);
        return true;
    }
    QStringList files() const { return watchedFiles; }
    QStringList directories() const { return watchedDirs; }
};
struct KDirWatch { enum Method { INotify, QFSWatch, Stat }; };
struct KFileSystemType {
    enum Type { Local, Nfs };
    static Type fileSystemType(const QString &) { return Local; }
};
struct TestTimer {
    int starts = 0;
    void start(int) { ++starts; }
};
class KDirWatchPrivate {
public:
    enum entryStatus { Normal, NonExistent };
    enum entryMode { UnknownMode, StatMode, INotifyMode, QFSWatchMode };
    struct Entry {
        QString path = QStringLiteral("/contract/file");
        entryStatus m_status = Normal;
        entryMode m_mode = UnknownMode;
        bool dirty = true;
        int freq = 0;
        bool isRoot() const { return path == QStringLiteral("/"); }
        QString parentDirectory() const { return QStringLiteral("/contract"); }
    };
    TestFileSystemWatcher *fsWatcher = new TestFileSystemWatcher;
    KDirWatch::Method m_preferredMethod = KDirWatch::QFSWatch;
    KDirWatch::Method m_nfsPreferredMethod = KDirWatch::QFSWatch;
    int m_nfsPollInterval = 5000, m_PollInterval = 500, freq = 500;
    int statEntries = 0, inotifyAttempts = 0, parentEntries = 0;
    TestTimer m_statRescanTimer;
    ~KDirWatchPrivate() { delete fsWatcher; }
    bool useINotify(Entry *) { ++inotifyAttempts; errno = EMFILE; return false; }
    void useFreq(Entry *entry, int interval) { entry->freq = interval; }
    void addEntry(void *, const QString &, Entry *, bool) { ++parentEntries; }
    bool useQFSWatch(Entry *);
    bool useStat(Entry *);
    void addWatch(Entry *);
};
#define connect(...) ((void)0)
#define QFileSystemWatcher TestFileSystemWatcher
#include "kdirwatch-methods.inc"
#undef QFileSystemWatcher
#undef connect

int main()
{
    {
        KDirWatchPrivate watcher;
        KDirWatchPrivate::Entry entry;
        watcher.fsWatcher->succeeds = false;
        watcher.addWatch(&entry);
        if (entry.m_mode != KDirWatchPrivate::StatMode || watcher.statEntries != 1 ||
            watcher.m_statRescanTimer.starts != 1 || watcher.inotifyAttempts != 1) {
            std::fputs("FAIL: rejected Qt registration did not reach live Stat fallback\n", stderr);
            return 1;
        }
    }
    {
        KDirWatchPrivate watcher;
        KDirWatchPrivate::Entry entry;
        watcher.addWatch(&entry);
        if (entry.m_mode != KDirWatchPrivate::QFSWatchMode || watcher.fsWatcher->adds != 1 ||
            watcher.statEntries != 0 || watcher.inotifyAttempts != 0)
            return 2;
    }
    for (bool directory : {false, true}) {
        KDirWatchPrivate watcher;
        KDirWatchPrivate::Entry entry;
        (directory ? watcher.fsWatcher->watchedDirs : watcher.fsWatcher->watchedFiles).append(entry.path);
        watcher.fsWatcher->succeeds = false;
        watcher.addWatch(&entry);
        if (entry.m_mode != KDirWatchPrivate::QFSWatchMode || watcher.fsWatcher->adds != 0 || watcher.statEntries != 0)
            return 3;
    }
    {
        KDirWatchPrivate watcher;
        KDirWatchPrivate::Entry entry;
        entry.m_status = KDirWatchPrivate::NonExistent;
        watcher.addWatch(&entry);
        if (watcher.parentEntries != 1 || watcher.fsWatcher->adds != 0 || watcher.statEntries != 0)
            return 4;
    }
    std::puts("PASS: registration failure falls back; successful, existing and parent watches remain live");
    return 0;
}
