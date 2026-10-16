// SPDX-License-Identifier: BSD-2-Clause
// Actual KDirWatch methods; watcher, resource-limit, timer and event boundaries are doubled.
#include <QString>
#include <QStringList>
#include <QMap>
#include <QList>
#include <QLoggingCategory>
#include <cstdio>
#include <cstdlib>
#include <cerrno>
#include <cstring>
#include <utility>
#include <sys/resource.h>

#define CHECK(x, message) do { if (!(x)) { std::fprintf(stderr, "FAIL: %s\n", message); std::_Exit(1); } } while (0)
#define HAVE_QFILESYSTEMWATCHER 1
#define HAVE_SYS_INOTIFY_H 1
// Select only the production method's platform branch, after native Qt headers.
#define Q_OS_NETBSD
Q_LOGGING_CATEGORY(KDIRWATCH, "ember.test.kdirwatch", QtWarningMsg)
static rlim_t softLimit = 8;
static bool limitFailure;
static int limitCalls, warnings;
static int testGetrlimit(int resource, struct rlimit *limit)
{
    CHECK(resource == RLIMIT_NOFILE, "resource limit selection");
    ++limitCalls;
    if (limitFailure) { errno = EIO; return -1; }
    limit->rlim_cur = softLimit;
    limit->rlim_max = softLimit;
    return 0;
}
class TestFileSystemWatcher {
public:
    bool succeeds = true;
    int adds = 0;
    QStringList watchedFiles, watchedDirs;
    bool addPath(const QString &path) {
        ++adds;
        if (!succeeds || watchedFiles.contains(path) || watchedDirs.contains(path)) {
            errno = EMFILE;
            return false;
        }
        watchedFiles.append(path);
        return true;
    }
    void removePath(const QString &path) { watchedFiles.removeAll(path); watchedDirs.removeAll(path); }
    // Keep the QFileSystemWatcher value-return API at this boundary.
    QStringList files() const { return watchedFiles; }
    QStringList directories() const { return watchedDirs; }
};
struct KDirWatch { enum Method { INotify, QFSWatch, Stat }; };
struct KFileSystemType {
    enum Type { Local, Nfs };
    static Type fileSystemType(const QString &) { return Local; }
};
struct TestTimer { int starts = 0; void start(int) { ++starts; } };
class KDirWatchPrivate {
public:
    enum entryStatus { Normal, NonExistent };
    enum entryMode { UnknownMode, StatMode, INotifyMode, QFSWatchMode };
    enum Event { NoChange, Changed, Created, Deleted };
    struct Entry {
        QString path = QStringLiteral("/contract/new");
        entryStatus m_status = Normal;
        entryMode m_mode = UnknownMode;
        bool dirty = true, isDir = false;
        int freq = 0;
        QList<Entry *> m_entries;
        bool isRoot() const { return path == QStringLiteral("/"); }
        QString parentDirectory() const { return QStringLiteral("/contract"); }
    };
    TestFileSystemWatcher *fsWatcher = new TestFileSystemWatcher;
    KDirWatch::Method m_preferredMethod = KDirWatch::QFSWatch, m_nfsPreferredMethod = KDirWatch::QFSWatch;
    int m_nfsPollInterval = 5000, m_PollInterval = 500, freq = 500;
    int statEntries = 0, inotifyAttempts = 0, parentEntries = 0;
    bool verboseDebug = false;
    int event = NoChange, scans = 0, emissions = 0;
    QMap<QString, Entry> m_mapEntries;
    TestTimer m_statRescanTimer;
    KDirWatchPrivate() = default;
    KDirWatchPrivate(const KDirWatchPrivate &) = delete;
    KDirWatchPrivate &operator=(const KDirWatchPrivate &) = delete;
    ~KDirWatchPrivate() { delete fsWatcher; }
    bool useINotify(Entry *) { ++inotifyAttempts; errno = EMFILE; return false; }
    void useFreq(Entry *entry, int interval) { entry->freq = interval; }
    void addEntry(void *, const QString &, Entry *, bool) { ++parentEntries; }
    int scanEntry(Entry *) { ++scans; return event; }
    void emitEvent(Entry *, int) { ++emissions; }
    bool useQFSWatch(Entry *);
    bool useStat(Entry *);
    void addWatch(Entry *);
    void fswEventReceived(const QString &);
};
#define getrlimit testGetrlimit
#define connect(...) ((void)0)
#define QFileSystemWatcher TestFileSystemWatcher
#include "kdirwatch-methods.inc"
#undef QFileSystemWatcher
#undef connect
#undef getrlimit

static void fillBudget(const KDirWatchPrivate &watcher)
{
    watcher.fsWatcher->watchedFiles = {QStringLiteral("/a"), QStringLiteral("/b")};
    watcher.fsWatcher->watchedDirs = {QStringLiteral("/c"), QStringLiteral("/d")};
}
static void resetLimit()
{
    softLimit = 8;
    limitFailure = false;
    limitCalls = warnings = 0;
}
static void checkStat(const KDirWatchPrivate &watcher, const KDirWatchPrivate::Entry &entry)
{
    CHECK(entry.m_mode == KDirWatchPrivate::StatMode && watcher.statEntries == 1,
          "live Stat fallback has one accounted entry");
    CHECK(entry.freq == 500 && watcher.m_statRescanTimer.starts == 1,
          "Stat fallback starts the existing polling timer");
}
int main()
{
    qInstallMessageHandler([](QtMsgType type, const QMessageLogContext &, const QString &) {
        if (type == QtWarningMsg) ++warnings;
    });
    {
        KDirWatchPrivate watcher;
        KDirWatchPrivate::Entry entry;
        fillBudget(watcher);
        watcher.addWatch(&entry);
        CHECK(entry.m_mode == KDirWatchPrivate::StatMode, "exact files-plus-directories budget must select Stat");
        checkStat(watcher, entry);
        CHECK(watcher.fsWatcher->adds == 0 && watcher.inotifyAttempts == 0, "budget fallback must not attempt another FD backend");
        watcher.addWatch(&entry);
        checkStat(watcher, entry);
        CHECK(limitCalls == 1, "polling entry remains stable on re-registration");
    }
    resetLimit();
    for (bool directory : {false, true}) {
        KDirWatchPrivate watcher;
        KDirWatchPrivate::Entry entry;
        fillBudget(watcher);
        (directory ? watcher.fsWatcher->watchedDirs : watcher.fsWatcher->watchedFiles).append(entry.path);
        watcher.fsWatcher->succeeds = false;
        softLimit = 0;
        watcher.addWatch(&entry);
        CHECK(entry.m_mode == KDirWatchPrivate::QFSWatchMode && watcher.fsWatcher->adds == 0 && limitCalls == 0,
              "existing watch survives a full or lowered budget");
        resetLimit();
    }
    {
        KDirWatchPrivate watcher;
        KDirWatchPrivate::Entry entry;
        fillBudget(watcher);
        watcher.fsWatcher->removePath(QStringLiteral("/a"));
        watcher.addWatch(&entry);
        CHECK(entry.m_mode == KDirWatchPrivate::QFSWatchMode && watcher.fsWatcher->adds == 1,
              "removing a real watcher path restores capacity");
        CHECK(watcher.fsWatcher->files().size() + watcher.fsWatcher->directories().size() == 4,
              "new registration fills exactly the allowed capacity");
        watcher.addWatch(&entry);
        CHECK(watcher.fsWatcher->adds == 1, "repeat registration does not double count");
    }
    resetLimit();
    {
        KDirWatchPrivate watcher;
        KDirWatchPrivate::Entry entry;
        watcher.fsWatcher->succeeds = false;
        watcher.addWatch(&entry);
        checkStat(watcher, entry);
        CHECK(watcher.inotifyAttempts == 1 && watcher.fsWatcher->files().isEmpty(), "failed registration retains existing fallback and consumes no quota");
        watcher.fsWatcher->succeeds = true;
        KDirWatchPrivate::Entry other;
        other.path = QStringLiteral("/other");
        watcher.addWatch(&other);
        CHECK(other.m_mode == KDirWatchPrivate::QFSWatchMode, "registration failure does not exhaust budget");
    }
    for (rlim_t limit : {rlim_t(0), rlim_t(1), rlim_t(RLIM_INFINITY)}) {
        resetLimit();
        softLimit = limit;
        KDirWatchPrivate watcher;
        delete watcher.fsWatcher;
        watcher.fsWatcher = nullptr;
        KDirWatchPrivate::Entry entry;
        watcher.addWatch(&entry);
        checkStat(watcher, entry);
        CHECK(warnings == 1 && watcher.fsWatcher == nullptr && watcher.inotifyAttempts == 0,
              "unusable limit warns and polls without creating a native watcher");
    }
    resetLimit();
    {
        limitFailure = true;
        KDirWatchPrivate watcher;
        KDirWatchPrivate::Entry entry;
        watcher.addWatch(&entry);
        checkStat(watcher, entry);
        CHECK(warnings == 1 && watcher.fsWatcher->adds == 0, "getrlimit error has visible polling fallback");
    }
    resetLimit();
    {
        KDirWatchPrivate watcher;
        fillBudget(watcher);
        KDirWatchPrivate::Entry entry;
        entry.m_mode = KDirWatchPrivate::QFSWatchMode;
        watcher.m_mapEntries.insert(entry.path, entry);
        watcher.fswEventReceived(entry.path);
        const auto &stored = watcher.m_mapEntries[entry.path];
        checkStat(watcher, stored);
        watcher.fswEventReceived(entry.path);
        checkStat(watcher, stored);
        CHECK(watcher.scans == 2 && watcher.fsWatcher->adds == 0,
              "repeated file events use the same budget and polling accounting");
    }
    resetLimit();
    {
        KDirWatchPrivate watcher;
        KDirWatchPrivate::Entry entry;
        entry.m_status = KDirWatchPrivate::NonExistent;
        watcher.addWatch(&entry);
        CHECK(watcher.parentEntries == 1 && limitCalls == 0, "missing paths retain parent registration");
    }
    std::puts("PASS: real KDirWatch budget, unique paths, failure fallback, stable Stat and repeated file events");
    return 0;
}
