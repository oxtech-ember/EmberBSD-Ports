// Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT
// Run in a disposable target process; --privileged also exercises affinity/RT.
#include <BS_thread_pool.hpp>
#include <sys/wait.h>
#include <cstdio>
#include <cstdlib>

#ifndef __NetBSD__
#error This contract requires the NetBSD native backend.
#endif
static_assert(BS::thread_pool_native_extensions);

static void check(bool ok, const char* message)
{
    if (!ok)
    {
        std::fprintf(stderr, "FAIL: %s\n", message);
        std::exit(1);
    }
}

int main(int argc, char** argv)
{
    const bool privileged = argc == 2 && std::string(argv[1]) == "--privileged";
    const int nice_before = getpriority(PRIO_PROCESS, getpid());
    check(BS::this_thread::set_os_thread_name("KiCad%worker"), "set literal percent name");
    check(BS::this_thread::get_os_thread_name() == "KiCad%worker", "name readback");
    check(!BS::this_thread::set_os_thread_name(std::string(PTHREAD_MAX_NAMELEN_NP, 'x')),
          "reject oversized name");
    check(BS::this_thread::get_os_thread_name() == "KiCad%worker", "failed name preserves value");

    int policy = 0;
    sched_param param = {};
    check(pthread_getschedparam(pthread_self(), &policy, &param) == 0 && policy == SCHED_OTHER,
          "ordinary time-sharing input");
    for (auto level : {BS::os_thread_priority::idle, BS::os_thread_priority::lowest,
                       BS::os_thread_priority::below_normal, BS::os_thread_priority::above_normal})
        check(!BS::this_thread::set_os_thread_priority(level), "unsupported per-thread nice fails");
    check(pthread_getschedparam(pthread_self(), &policy, &param) == 0 && policy == SCHED_OTHER,
          "unsupported operation preserves policy");
    check(getpriority(PRIO_PROCESS, getpid()) == nice_before, "thread priority never changes process nice");
    check(BS::this_thread::set_os_thread_priority(BS::os_thread_priority::normal), "normal priority");
    check(BS::this_thread::get_os_thread_priority() == BS::os_thread_priority::normal,
          "normal priority readback");

    const auto thread_before = BS::this_thread::get_os_thread_affinity();
    const auto process_before = BS::get_os_process_affinity();
    const long count = sysconf(_SC_NPROCESSORS_CONF);
    check(count > 0, "configured CPU count");
    std::vector<bool> invalid(static_cast<std::size_t>(count) + 1, false);
    check(!BS::this_thread::set_os_thread_affinity(invalid), "reject empty thread selection");
    check(!BS::set_os_process_affinity(invalid), "reject empty process selection");
    invalid.back() = true;
    check(!BS::this_thread::set_os_thread_affinity(invalid), "reject out-of-range thread CPU");
    check(!BS::set_os_process_affinity(invalid), "reject out-of-range process CPU");
    check(BS::this_thread::get_os_thread_affinity() == thread_before &&
          BS::get_os_process_affinity() == process_before, "invalid masks preserve affinity");
    if (!process_before)
    {
        BS::light_thread_pool automatic;
        check(automatic.get_thread_count() == std::max(1U, std::thread::hardware_concurrency()),
              "unbound process retains automatic worker count");
    }

    if (privileged)
    {
        check(geteuid() == 0, "privileged test user");
        std::vector<bool> mask(static_cast<std::size_t>(count), false);
        mask[0] = true;
        check(BS::this_thread::set_os_thread_affinity(mask), "bind current thread");
        check(BS::this_thread::get_os_thread_affinity() == mask, "thread affinity readback");
        check(BS::set_os_process_affinity(mask), "bind process");
        check(BS::get_os_process_affinity() == mask, "process affinity readback");
        for (auto level : {BS::os_thread_priority::highest, BS::os_thread_priority::realtime})
        {
            const bool set = BS::this_thread::set_os_thread_priority(level);
            const auto readback = BS::this_thread::get_os_thread_priority();
            const bool reset = BS::this_thread::set_os_thread_priority(BS::os_thread_priority::normal);
            check(set && readback == level && reset, "RT preset and normal restoration");
        }
    }

    const pid_t child = fork();
    check(child >= 0, "fork process-priority test");
    if (child == 0)
    {
        const bool set = BS::set_os_process_priority(BS::os_process_priority::below_normal);
        const bool readback = BS::get_os_process_priority() == BS::os_process_priority::below_normal;
        _exit(set && readback ? 0 : 1);
    }
    int status = 0;
    check(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 0,
          "isolated process nice round-trip");
    check(getpriority(PRIO_PROCESS, getpid()) == nice_before, "parent nice preserved");

    BS::priority_thread_pool pool(2, [] {
        check(!BS::this_thread::set_os_thread_priority(BS::os_thread_priority::below_normal),
              "KiCad worker initializer sees unsupported priority");
    });
    auto task = pool.submit_task([] { return 42; });
    check(task.get() == 42, "KiCad-style worker initializer still executes tasks");
    std::puts("NetBSD thread-pool native contracts PASS");
}
