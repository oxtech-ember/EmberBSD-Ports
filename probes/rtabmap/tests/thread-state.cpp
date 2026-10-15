// SPDX-License-Identifier: MIT
// Origin: EmberBSD (AI-assisted). Production UThread lifecycle/state regression.
#include <rtabmap/utilite/UThread.h>
#include <rtabmap/utilite/USemaphore.h>
#include <rtabmap/utilite/UMutex.h>
#include <cstdio>
#include <memory>
#include <thread>
#include <vector>

extern "C" {
unsigned char ember_uthread_size[sizeof(UThread)];
unsigned char ember_uthread_alignment[alignof(UThread)];
}

class BlockingThread final : public UThread {
public:
    void waitUntilEntered() { entered_.acquire(); }
    int completedLoops() const { return completed_; }
    ~BlockingThread() override { join(true); }
private:
    void mainLoopBegin() override { entered_.release(); }
    void mainLoop() override {
        work_.acquire();
        ++completed_;
    }
    void mainLoopKill() override { work_.release(); }
    USemaphore entered_;
    USemaphore work_;
    int completed_ = 0;
};

int main() {
    constexpr int cycles = 8;
    constexpr int width = 4;
    int completed = 0;
    unsigned long observations = 0;
    // A normal unlocked mutex must be safe to destroy. Helgrind checks the
    // production UMutex destructor rather than a replacement implementation.
    { UMutex normal; normal.lock(); normal.unlock(); }
    for (int cycle = 0; cycle < cycles; ++cycle) {
        std::vector<std::unique_ptr<BlockingThread>> workers;
        for (int i = 0; i < width; ++i) {
            workers.emplace_back(new BlockingThread);
            workers.back()->start();
            workers.back()->waitUntilEntered();
        }
        USemaphore observerReady;
        USemaphore observerStop;
        std::thread observer([&]() {
            unsigned long local = 0;
            observerReady.release();
            do {
                for (const auto& worker : workers) {
                    (void)worker->isRunning();
                    (void)worker->isCreating();
                    (void)worker->isKilled();
                    (void)worker->isIdle();
                    ++local;
                }
                std::this_thread::yield();
            } while (!observerStop.acquireTry(1));
            observations += local;
        });
        observerReady.acquire();
        // Each worker stays blocked until join(true) has checked its handle
        // and kill() posts work_. The observer concurrently polls only state.
        for (const auto& worker : workers) {
            worker->join(true);
            if (!worker->isIdle() || worker->completedLoops() != 1) return 1;
            completed += worker->completedLoops();
        }
        observerStop.release();
        observer.join();
    }
    if (completed != cycles * width || observations == 0) return 2;
    std::printf("PASS UThread: cycles=%d threads=%d completed=%d observations=%lu sizeof=%zu alignof=%zu\n",
        cycles, width, completed, observations, sizeof(UThread), alignof(UThread));
}
