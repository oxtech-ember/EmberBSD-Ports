// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD; AI-assisted public Qt mutex ABI and descriptor consumer.
#include <QtCore/QMutex>
#include <QtCore/QDeadlineTimer>
#include <atomic>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <memory>
#include <sys/resource.h>
#include <thread>
#include <vector>

#define CHECK(x) do { if (!(x)) { \
    std::fprintf(stderr, "FAIL %s:%d: %s (errno=%d)\n", __FILE__, __LINE__, #x, errno); \
    std::exit(1); \
} } while (false)

static int descriptors(rlim_t limit)
{
    int count = 0;
    for (rlim_t fd = 0; fd < limit; ++fd) {
        errno = 0;
        if (fcntl(int(fd), F_GETFD) != -1)
            ++count;
        else
            CHECK(errno == EBADF);
    }
    return count;
}

int main()
{
    static_assert(sizeof(QMutex) == sizeof(void *));
    static_assert(sizeof(QBasicMutex) == sizeof(void *));
    rlimit limit;
    CHECK(getrlimit(RLIMIT_NOFILE, &limit) == 0);
    CHECK(limit.rlim_max >= 1024);
    limit.rlim_cur = 1024;
    CHECK(setrlimit(RLIMIT_NOFILE, &limit) == 0);
    const int before = descriptors(limit.rlim_cur);
    constexpr int count = 145;
    auto locks = std::make_unique<QMutex[]>(count);
    std::atomic<int> ready{0}, acquired{0};
    for (int i = 0; i < count; ++i)
        locks[i].lock();
    std::vector<std::thread> threads;
    for (int i = 0; i < count; ++i) {
        threads.emplace_back([&, i] {
            ready.fetch_add(1);
            CHECK(locks[i].tryLock(QDeadlineTimer(10000)));
            acquired.fetch_add(1);
            locks[i].unlock();
        });
    }
    QDeadlineTimer readyDeadline(5000);
    while (ready.load() != count) {
        CHECK(!readyDeadline.hasExpired());
        std::this_thread::yield();
    }
    // Allow each worker to enter the held mutex's timed wait path.
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    const int peak = descriptors(limit.rlim_cur);
    for (int i = 0; i < count; ++i)
        locks[i].unlock();
    for (auto &thread : threads)
        thread.join();
    CHECK(acquired.load() == count);
    CHECK(peak == before);
    CHECK(descriptors(limit.rlim_cur) == before);
    QRecursiveMutex recursive;
    CHECK(recursive.tryLock());
    CHECK(recursive.tryLock(0));
    recursive.unlock();
    recursive.unlock();
    std::printf("Qt public mutex ABI: PASS, workers=%d fd_before=%d fd_peak=%d\n",
                count, before, peak);
}
