// SPDX-License-Identifier: MIT
// Origin: EmberBSD (AI-assisted). Production UThread completion regression.
#include <rtabmap/utilite/UThread.h>
#include <rtabmap/utilite/USemaphore.h>
#include <rtabmap/utilite/ULogger.h>
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <string>
#include <unistd.h>

class NaturalThread final : public UThread {
public:
    explicit NaturalThread(bool joinSelf = false) : joinSelf_(joinSelf) {}
    void waitUntilEntered() { entered_.acquire(); }
    void releaseWork() { work_.release(); }
    int completed() const { return completed_; }
private:
    void mainLoopBegin() override { entered_.release(); }
    void mainLoop() override {
        work_.acquire();
        // The final log check requires the production self-join rejection.
        if (joinSelf_) join();
        ++completed_;
        kill();
    }
    const bool joinSelf_;
    USemaphore entered_;
    USemaphore work_;
    int completed_ = 0;
};

int main() {
    char logPath[] = "thread-self-join.XXXXXX";
    const int logFd = mkstemp(logPath);
    if (logFd < 0 || close(logFd) != 0) return 2;
    ULogger::setType(ULogger::kTypeFile, logPath, false);
    ULogger::setLevel(ULogger::kError);
    ULogger::setPrintTime(false);
    ULogger::setPrintWhere(false);
    constexpr int count = 64;
    for (int i = 0; i <= count; ++i) {
        NaturalThread thread(i == count);
        thread.start();
        thread.waitUntilEntered();
        thread.releaseWork();
        thread.join();
        if (!thread.isIdle() || thread.completed() != 1) return 1;
    }
    ULogger::flush();
    ULogger::setType(ULogger::kTypeNoLog);
    std::ifstream input(logPath);
    const std::string log((std::istreambuf_iterator<char>(input)),
                          std::istreambuf_iterator<char>());
    input.close();
    if (unlink(logPath) != 0) return 3;
    const std::string expected = "Thread cannot join itself";
    const auto rejection = log.find(expected);
    if (rejection == std::string::npos ||
        log.find(expected, rejection + expected.size()) != std::string::npos) return 4;
    std::printf("PASS UThread: natural-completion=%d self-join-rejections=1\n", count);
}
