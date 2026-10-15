// SPDX-License-Identifier: MIT
// Origin: EmberBSD (AI-assisted). Actual OS thread completion contract.
#include <rtabmap/utilite/UThread.h>
#include <rtabmap/utilite/USemaphore.h>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <vector>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

static void require(bool condition, const char *message)
{
    if (!condition) throw std::runtime_error(message);
}

struct Gate {
    std::mutex mutex;
    std::condition_variable changed;
    bool entered = false;
    bool allowExit = false;
    bool done = false;
    bool joinReturned = false;
};

struct Completion {
    UThread *owner = nullptr;
    Gate *gate = nullptr;
    std::atomic<int> *count = nullptr;
    USemaphore *finished = nullptr;
    ~Completion() {
        if (!owner) return;
        if (gate) {
            std::unique_lock<std::mutex> lock(gate->mutex);
            gate->entered = true;
            gate->changed.notify_all();
            gate->changed.wait(lock, [&] { return gate->allowExit; });
        }
        // Self-join must also be rejected during actual TLS destruction.
        owner->join();
        if (count) ++*count;
        if (finished) finished->release();
        if (gate) {
            std::lock_guard<std::mutex> lock(gate->mutex);
            gate->done = true;
            gate->changed.notify_all();
        }
    }
};
static thread_local Completion completion;

class GatedThread final : public UThread {
public:
    explicit GatedThread(Gate &gate) : gate_(gate) {}
private:
    void mainLoop() override {
        completion.owner = this;
        completion.gate = &gate_;
        kill();
    }
    Gate &gate_;
};

static void checkTlsCompletion()
{
    for (int cycle = 0; cycle < 8; ++cycle) {
        Gate gate;
        GatedThread worker(gate);
        worker.start();
        {
            std::unique_lock<std::mutex> lock(gate.mutex);
            gate.changed.wait(lock, [&] { return gate.entered; });
        }
        // The guard releases the destructor after an early join return, or
        // after a bounded wait when a correct OS join remains blocked. The
        // assertion checks the destructor's actual completion, not elapsed time.
        std::thread releaseGuard([&] {
            std::unique_lock<std::mutex> lock(gate.mutex);
            gate.changed.wait_for(lock, std::chrono::milliseconds(100),
                                 [&] { return gate.joinReturned; });
            gate.allowExit = true;
            gate.changed.notify_all();
        });
        worker.join();
        bool completedAtReturn;
        {
            std::lock_guard<std::mutex> lock(gate.mutex);
            completedAtReturn = gate.done;
            gate.joinReturned = true;
            gate.changed.notify_all();
        }
        releaseGuard.join();
        {
            std::unique_lock<std::mutex> lock(gate.mutex);
            gate.changed.wait(lock, [&] { return gate.done; });
        }
        require(completedAtReturn, "join returned before the TLS destructor completed");
        worker.join(); // An already reaped thread is safe to join again.
    }
}

class ReusableThread final : public UThread {
public:
    std::atomic<int> bodies{0};
    std::atomic<int> destructors{0};
    std::atomic<bool> badReuse{false};
    USemaphore bodyFinished;
private:
    void mainLoop() override {
        completion.owner = this;
        completion.count = &destructors;
        const int previous = bodies++;
        if (destructors.load() != previous) badReuse = true;
        kill();
    }
    void mainLoopEnd() override { bodyFinished.release(); }
};

static void checkReuse()
{
    ReusableThread worker;
    for (int cycle = 0; cycle < 12; ++cycle) {
        worker.start();
        worker.bodyFinished.acquire();
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
        while (!worker.isIdle() && std::chrono::steady_clock::now() < deadline)
            std::this_thread::yield();
        require(worker.isIdle(), "worker did not become idle");
        // No join here. The next start must reap this previous generation.
    }
    worker.join();
    worker.join();
    require(worker.bodies == 12 && worker.destructors == 12 && !worker.badReuse,
            "start reused a thread before its preceding TLS destructor completed");
    require(worker.getThreadHandle() == 0 && worker.getThreadId() == 0,
            "successful join must clear the creator-owned handle and ID");
}

class SharedJoinThread final : public UThread {
public:
    std::atomic<int> destructors{0};
    USemaphore entered;
    USemaphore finished;
private:
    void mainLoop() override {
        completion.owner = this;
        completion.count = &destructors;
        completion.finished = &finished;
        entered.release();
        work_.acquire();
    }
    void mainLoopKill() override { work_.release(); }
    USemaphore work_;
};

static void checkConcurrentJoiners()
{
    for (int cycle = 0; cycle < 8; ++cycle) {
        SharedJoinThread worker;
        worker.start();
        worker.entered.acquire();
        std::atomic<bool> early{false};
        std::vector<std::thread> joiners;
        for (int i = 0; i < 4; ++i) {
            joiners.emplace_back([&] {
                worker.join(true);
                if (worker.destructors != 1) early = true;
            });
        }
        for (auto &joiner : joiners) joiner.join();
        worker.finished.acquire();
        require(!early && worker.destructors == 1 && worker.isIdle(),
                "concurrent joiners did not all observe complete thread termination");
        require(worker.getThreadHandle() == 0 && worker.getThreadId() == 0,
                "concurrent joiners must reap the handle exactly once");
    }
}

static bool checkFailedCreate()
{
#if defined(__linux__)
    // A native non-root child can deterministically reject pthread_create.
    // This changes only the child's resource limit, not any other build.
    if (geteuid() != 0) {
        const pid_t child = fork();
        require(child >= 0, "cannot fork failed-create test");
        if (child == 0) {
            struct rlimit limit;
            if (getrlimit(RLIMIT_NPROC, &limit) != 0) _exit(2);
            limit.rlim_cur = 0;
            if (setrlimit(RLIMIT_NPROC, &limit) != 0) _exit(3);
            ReusableThread worker;
            worker.start();
            if (!worker.isIdle()) { worker.join(true); _exit(77); }
            worker.join();
            _exit(worker.getThreadHandle() == 0 && worker.getThreadId() == 0 ? 0 : 4);
        }
        int status = 0;
        require(waitpid(child, &status, 0) == child && WIFEXITED(status),
                "failed-create test did not exit normally");
        if (WEXITSTATUS(status) == 77) return false;
        require(WEXITSTATUS(status) == 0, "failed create did not retain idle/empty state");
        return true;
    }
#endif
    return false;
}

int main(int argc, char **argv)
{
    try {
        require(argc == 1 || (argc == 2 && std::strcmp(argv[1], "--join-only") == 0),
                "usage: thread-join [--join-only]");
        checkTlsCompletion();
        checkReuse();
        checkConcurrentJoiners();
        // Helgrind reports an intentional EAGAIN as a pthread API error. Its
        // ordinary lifecycle run uses --join-only; normal and Memcheck runs
        // separately exercise the real resource-failure branch without it.
        const bool failedCreate = argc == 1 && checkFailedCreate();
        std::printf("PASS OS thread join: TLS=8 reuse=12 joiners=8x4 failed-create=%s\n",
                    argc == 2 ? "separate-functional-check" :
                    (failedCreate ? "verified" : "not-exercised-on-this-platform"));
        return 0;
    } catch (const std::exception &error) {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
}
