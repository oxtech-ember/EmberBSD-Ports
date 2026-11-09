# Native thread-pool operations

Enable `BS_THREAD_POOL_NATIVE_EXTENSIONS` before including the common provider.
The NetBSD backend uses native process/thread affinity, thread names, process
nice values and POSIX thread scheduling. It does not change process priority
to emulate a thread-local request.

NetBSD's `SCHED_OTHER` uses a dynamic priority and only accepts `PRI_NONE` when
setting it. Consequently, the thread presets `idle`, `lowest`, `below_normal`
and `above_normal` return `false` without changing anything. `normal` selects
`SCHED_OTHER`; `highest` and `realtime` use RR/FIFO and can fail for lack of
permissions. The getter classifies any `SCHED_OTHER` thread as `normal`, not by
its momentary dynamic priority. See the [NetBSD scheduling contract](https://man.netbsd.org/sched.3).

An empty native affinity mask means unbound. The getter returns `nullopt` for
it, retaining the pool's ordinary automatic thread count. A setter rejects an
all-false or invalid CPU selection. Native process affinity reads the first
live thread's mask and writes all current threads; it is not an intersection
of individually different thread masks. Affinity changes require the platform's
normal permission; this port does not change system policy.

Build `tests/netbsd-native.cpp` with the selected target C++17-or-later compiler,
`-DBS_THREAD_POOL_NATIVE_EXTENSIONS`, the installed provider and `-pthread`.
Run it with a bounded timeout as an ordinary user. A separate root invocation
with `--privileged` checks affinity and RR/FIFO operations in that disposable
process. Tests do not alter system-wide scheduler settings.

`tests/affinity-memory.py --header /prepared/include/BS_thread_pool.hpp
--output /work/affinity-memory.cpp` extracts the actual cpuset conversion and
ownership helpers into a controlled native-API fixture. Build that output with
the selected host compiler and ASan/UBSan, including leak detection. It covers
allocation, query, membership, apply and exception failure paths. This is a host
memory check of the actual helper logic; the target test above separately checks
the native syscalls. Clang 23 does not support ASan for aarch64 NetBSD.
