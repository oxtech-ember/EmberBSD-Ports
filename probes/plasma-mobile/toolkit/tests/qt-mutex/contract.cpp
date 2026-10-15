// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD; AI-assisted contract for actual Qt private mutex sources.
#include <QtCore/qglobal.h>
#include <QtCore/qdeadlinetimer.h>
#include <QtCore/qmutex.h>
#include <QtCore/private/qglobal_p.h>
#include <QtCore/private/qcore_unix_p.h>
#include <QtCore/private/qfreelist_p.h>
#include <pthread.h>
#include <semaphore.h>
#include <sys/resource.h>
#include <fcntl.h>
#include <unistd.h>
#include <atomic>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <thread>
#include <vector>
#include <unordered_map>

#define CHECK(x) do { if (!(x)) { \
    std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #x); \
    std::exit(1); \
} } while (false)

static std::atomic<int> waits{0};
static int liveMutexes, liveConditions, liveAttrs;
static const char *fault;
static const char *expectedFatal;
static std::unordered_map<sem_t *, int> semFds;
static int semFailures;
static unsigned int *timeoutToken;
static clockid_t selectedClock = CLOCK_REALTIME;

[[maybe_unused]] static bool inject(const char *operation)
{
    if (fault && std::strcmp(fault, operation) == 0) {
        fault = nullptr;
        return true;
    }
    return false;
}

[[maybe_unused]] static int mutexInit(pthread_mutex_t *m, const pthread_mutexattr_t *a)
{
    if (inject("mutex_init"))
        return EAGAIN;
    const int result = pthread_mutex_init(m, a);
    liveMutexes += result == 0;
    return result;
}
[[maybe_unused]] static int mutexDestroy(pthread_mutex_t *m)
{
    const int result = pthread_mutex_destroy(m);
    liveMutexes -= result == 0;
    return result;
}
[[maybe_unused]] static int attrInit(pthread_condattr_t *a)
{
    if (inject("attr_init"))
        return EAGAIN;
    const int result = pthread_condattr_init(a);
    liveAttrs += result == 0;
    return result;
}
[[maybe_unused]] static int attrDestroy(pthread_condattr_t *a)
{
    const int result = pthread_condattr_destroy(a);
    liveAttrs -= result == 0;
    if (inject("attr_destroy"))
        return EINVAL;
    return result;
}
[[maybe_unused]] static int attrSetClock(pthread_condattr_t *, clockid_t clock)
{
    CHECK(clock == CLOCK_MONOTONIC);
    selectedClock = clock;
    return inject("attr_setclock") ? EINVAL : 0;
}
[[maybe_unused]] static int condInit(pthread_cond_t *c, const pthread_condattr_t *a)
{
    if (inject("cond_init"))
        return EAGAIN;
    const int result = pthread_cond_init(c, a);
    liveConditions += result == 0;
    return result;
}
[[maybe_unused]] static int condDestroy(pthread_cond_t *c)
{
    const int result = pthread_cond_destroy(c);
    liveConditions -= result == 0;
    return result;
}
[[maybe_unused]] static int condWait(pthread_cond_t *c, pthread_mutex_t *m)
{
    waits.fetch_add(1);
    if (inject("wait"))
        return EINVAL;
    return pthread_cond_wait(c, m);
}
[[maybe_unused]] static int condTimedWait(pthread_cond_t *c, pthread_mutex_t *m, const timespec *t)
{
    waits.fetch_add(1);
    if (inject("timedwait"))
        return EINVAL;
    if (inject("timeout_race")) {
        CHECK(timeoutToken != nullptr);
        ++*timeoutToken; // caller still holds the event mutex
        return ETIMEDOUT;
    }
    return pthread_cond_timedwait(c, m, t);
}
[[maybe_unused]] static int condSignal(pthread_cond_t *c)
{
    if (inject("signal"))
        return EINVAL;
    return pthread_cond_signal(c);
}

// Model EmberBSD's one-descriptor-per-unnamed-semaphore contract on the host.
[[maybe_unused]] static int semInit(sem_t *s, int pshared, unsigned int value)
{
    CHECK(pshared == 0 && value == 0);
    const int fd = open("/dev/null", O_RDONLY);
    if (fd == -1) {
        CHECK(errno == EMFILE);
        ++semFailures;
        return -1;
    }
    CHECK(semFds.emplace(s, fd).second);
    return 0;
}
[[maybe_unused]] static int semDestroy(sem_t *s)
{
    const auto item = semFds.find(s);
    if (item == semFds.end()) {
        errno = EINVAL;
        return -1;
    }
    CHECK(close(item->second) == 0);
    semFds.erase(item);
    return 0;
}

[[maybe_unused, noreturn]] static int unexpectedSemWait(sem_t *)
{
    std::fputs("Unexpected semaphore operation in capacity-only baseline\n", stderr);
    std::exit(99);
}
[[maybe_unused, noreturn]] static int unexpectedSemTimedWait(sem_t *s, const timespec *)
{
    unexpectedSemWait(s);
}

[[maybe_unused, noreturn]] static void fatal(const char *, const char *operation, int code)
{
    CHECK(expectedFatal && std::strcmp(expectedFatal, operation) == 0);
    CHECK(code != 0);
    if (std::strstr(operation, "init") || std::strstr(operation, "attr_destroy") || std::strstr(operation, "setclock"))
        CHECK(liveMutexes == 0 && liveConditions == 0 && liveAttrs == 0);
    std::fprintf(stderr, "EXPECTED_FATAL %s %d\n", operation, code);
    std::_Exit(42);
}
[[maybe_unused, noreturn]] static void fatal(const char *message)
{
    CHECK(expectedFatal && std::strcmp(expectedFatal, "overflow") == 0);
    CHECK(std::strstr(message, "overflow"));
    std::fprintf(stderr, "EXPECTED_FATAL overflow\n");
    std::_Exit(42);
}

// Select only the private backend after the host Qt and system headers load.
// Public host Qt types keep their native platform configuration.
#ifdef TEST_FIXED
#define Q_OS_NETBSD
#endif
#ifdef TEST_COND_CLOCK
// Exercise the target clock-selection branch; the host lacks setclock().
// Only constructor cases run in this variant, never timed native waits.
#undef QT_FEATURE_pthread_condattr_setclock
#define QT_FEATURE_pthread_condattr_setclock 1
#define QWaitConditionClockId CLOCK_MONOTONIC
#define pthread_condattr_setclock attrSetClock
#endif
#define QMutexPrivate TestedMutexPrivate
#include "qmutex_p.h"
#define sem_init semInit
#define sem_destroy semDestroy
#define sem_wait unexpectedSemWait
#define sem_post unexpectedSemWait
#define sem_timedwait unexpectedSemTimedWait
#define pthread_mutex_init mutexInit
#define pthread_mutex_destroy mutexDestroy
#define pthread_condattr_init attrInit
#define pthread_condattr_destroy attrDestroy
#define pthread_cond_init condInit
#define pthread_cond_destroy condDestroy
#define pthread_cond_wait condWait
#define pthread_cond_timedwait condTimedWait
#define pthread_cond_signal condSignal
#undef qFatal
#define qFatal fatal
#include "qmutex_unix.cpp"
#undef pthread_cond_signal
#undef pthread_cond_timedwait
#undef pthread_cond_wait
#undef pthread_cond_destroy
#undef pthread_cond_init
#undef pthread_condattr_destroy
#undef pthread_condattr_init
#undef pthread_mutex_destroy
#undef pthread_mutex_init
#undef sem_timedwait
#undef sem_post
#undef sem_wait
#undef sem_destroy
#undef sem_init
#undef QMutexPrivate

#include "freelist-constants.h"

static int descriptorCount()
{
    int count = 0;
    for (int fd = 0; fd < 1024; ++fd) {
        errno = 0;
        if (fcntl(fd, F_GETFD) != -1 || errno != EBADF)
            ++count;
    }
    return count;
}

static void poolCase()
{
    rlimit limit;
    CHECK(getrlimit(RLIMIT_NOFILE, &limit) == 0 && limit.rlim_max >= 1024);
    limit.rlim_cur = 1024;
    CHECK(setrlimit(RLIMIT_NOFILE, &limit) == 0);
    const int before = descriptorCount();
    {
        QFreeList<TestedMutexPrivate, FreeListConstants> pool;
        std::vector<int> ids;
        for (int i = 0; i < 145; ++i)
            ids.push_back(pool.next());
        const int peak = descriptorCount();
        std::printf("POOL ids=145 fd_before=%d fd_peak=%d sem_failures=%d\n",
                    before, peak, semFailures);
        std::fflush(stdout);
        CHECK(semFailures == 0);
#ifdef TEST_FIXED
        CHECK(peak == before && liveMutexes == 1168 && liveConditions == 1168);
#endif
        for (int id : ids)
            pool.release(id);
        for (int i = 0; i < 100; ++i) {
            const int id = pool.next();
            pool.release(id);
        }
        CHECK(descriptorCount() == before);
    }
    CHECK(semFds.empty() && liveMutexes == 0 && liveConditions == 0 && liveAttrs == 0);
    CHECK(descriptorCount() == before);
}

#ifdef TEST_FIXED
static void waitForCalls(int count)
{
    const auto limit = std::chrono::steady_clock::now() + std::chrono::seconds(2);
    while (waits.load() < count) {
        CHECK(std::chrono::steady_clock::now() < limit);
        std::this_thread::yield();
    }
}

static void eventCase()
{
    TestedMutexPrivate event;
    event.wakeUp();
    CHECK(event.wait(QDeadlineTimer(0)));
    for (int i = 0; i < 3; ++i)
        event.wakeUp();
    for (int i = 0; i < 3; ++i)
        CHECK(event.wait(QDeadlineTimer(0)));
    const auto before = std::chrono::steady_clock::now();
    CHECK(!event.wait(QDeadlineTimer(10)));
    const auto elapsed = std::chrono::steady_clock::now() - before;
    CHECK(elapsed >= std::chrono::milliseconds(8) && elapsed < std::chrono::seconds(2));
    timeoutToken = &event.wakeups;
    fault = "timeout_race";
    CHECK(event.wait(QDeadlineTimer(10)) && event.wakeups == 0);
    timeoutToken = nullptr;
    std::atomic<int> acquired{0};
    waits.store(0);
    std::thread waiter([&] { if (event.wait(QDeadlineTimer(2000))) acquired.fetch_add(1); });
    waitForCalls(1);
    CHECK(pthread_mutex_lock(&event.mutex) == 0);
    CHECK(pthread_cond_signal(&event.cond) == 0); // no token: spurious wakeup
    CHECK(pthread_mutex_unlock(&event.mutex) == 0);
    waitForCalls(2);
    CHECK(acquired.load() == 0);
    event.wakeUp();
    waiter.join();
    CHECK(acquired.load() == 1);
    constexpr int threads = 4, rounds = 1000;
    std::vector<std::thread> consumers;
    acquired.store(0);
    for (int i = 0; i < threads; ++i)
        consumers.emplace_back([&] {
            for (int n = 0; n < rounds; ++n) {
                CHECK(event.wait(QDeadlineTimer(5000)));
                acquired.fetch_add(1);
            }
        });
    for (int i = 0; i < threads * rounds; ++i)
        event.wakeUp();
    for (auto &consumer : consumers)
        consumer.join();
    CHECK(acquired.load() == threads * rounds);
    CHECK(!event.wait(QDeadlineTimer(0)));
    waits.store(0);
    pthread_t cancelThread;
    CHECK(pthread_create(&cancelThread, nullptr, [](void *p) -> void * {
        static_cast<TestedMutexPrivate *>(p)->wait();
        return nullptr;
    }, &event) == 0);
    waitForCalls(1);
    CHECK(pthread_cancel(cancelThread) == 0);
    void *result = nullptr;
    CHECK(pthread_join(cancelThread, &result) == 0 && result == PTHREAD_CANCELED);
    event.wakeUp();
    CHECK(event.wait(QDeadlineTimer(0)));
}
#endif

int main(int argc, char **argv)
{
    CHECK(argc == 2);
    if (std::strcmp(argv[1], "pool") == 0) {
        poolCase();
#ifdef TEST_FIXED
    } else if (std::strcmp(argv[1], "clock") == 0) {
        { TestedMutexPrivate event; }
        CHECK(selectedClock == CLOCK_MONOTONIC);
        CHECK(liveMutexes == 0 && liveConditions == 0 && liveAttrs == 0);
    } else if (std::strcmp(argv[1], "event") == 0) {
        eventCase();
        CHECK(liveMutexes == 0 && liveConditions == 0 && liveAttrs == 0);
    } else {
        const char *mode = argv[1];
        CHECK(std::strcmp(mode, "mutex_init") == 0 || std::strcmp(mode, "attr_init") == 0 ||
              std::strcmp(mode, "cond_init") == 0 || std::strcmp(mode, "attr_destroy") == 0 ||
              std::strcmp(mode, "attr_setclock") == 0 || std::strcmp(mode, "wait") == 0 ||
              std::strcmp(mode, "timedwait") == 0 || std::strcmp(mode, "signal") == 0 ||
              std::strcmp(mode, "overflow") == 0);
        fault = mode;
        expectedFatal = std::strcmp(mode, "mutex_init") == 0 ? "pthread_mutex_init" :
            std::strcmp(mode, "attr_init") == 0 ? "pthread_condattr_init" :
            std::strcmp(mode, "attr_setclock") == 0 ? "pthread_condattr_setclock" :
            std::strcmp(mode, "cond_init") == 0 ? "pthread_cond_init" :
            std::strcmp(mode, "attr_destroy") == 0 ? "pthread_condattr_destroy" :
            std::strcmp(mode, "signal") == 0 ? "pthread_cond_signal" :
            std::strcmp(mode, "overflow") == 0 ? "overflow" : "pthread_cond_wait";
        TestedMutexPrivate event;
        if (std::strcmp(mode, "signal") == 0)
            event.wakeUp();
        else if (std::strcmp(mode, "overflow") == 0) {
            event.wakeups = (std::numeric_limits<unsigned int>::max)();
            event.wakeUp();
        } else
            event.wait(std::strcmp(mode, "timedwait") == 0 ? QDeadlineTimer(100) : QDeadlineTimer(QDeadlineTimer::Forever));
        CHECK(false);
#endif
    }
    std::puts("Qt private mutex source contract: PASS");
    return 0;
}
