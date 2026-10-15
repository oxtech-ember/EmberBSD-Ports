# NetBSD private QMutex event

Qt 6.12.0's generic Unix QMutex fallback uses one unnamed semaphore per
private mutex object. EmberBSD's `_ksem_init` allocates a process descriptor
for each semaphore. Qt's free list constructs blocks of 16, 128, and 1024
objects. The 145th live private object can therefore allocate 1168 descriptors.
Released objects remain in that pool until its destructor runs.

`EMFILE` means this process exhausted its descriptor limit. It does not mean
that `kern.posix.semmax` was reached. That kernel check returns `ENFILE`;
`kern.posix.semcnt` counts named semaphores. This correction does not establish
the cause of an application's separate graphics crash.

The qt6-qtbase 6.12.0nb1 recipe uses a private pthread mutex, condition, and
pending-wakeup count on the NetBSD ABI. It preserves signals sent before a
wait, repeated signals, deadlines, spurious-wakeup handling, and timeout races.
It uses Qt's `QWaitConditionClockId` and `deadlineToAbstime` conversion.
Unexpected pthread failures terminate with a diagnostic. They cannot become
a successful lock. Other platform branches remain unchanged.

## Source contract

Use native Qt 6.12.0 with its matching private headers and an ASan/UBSan compiler.
The runner verifies the source archive against the recipe's SHA512.
It checks both patch SHA1 values after pkgsrc RCS-line canonicalization.
A wrong checksum stops before extraction or compilation.

```sh
ruby source-contract.rb /absolute/qtbase-everywhere-src-6.12.0.tar.xz /absolute/new-source-checks
ruby target-contract.rb /absolute/cross-tools /absolute/emberbsd-sysroot \
    /absolute/new-source-checks /absolute/new-target-checks
```

The host test compiles the actual patched `qmutex_p.h` and `qmutex_unix.cpp`.
It uses Qt's real `QFreeList` and constants extracted from actual `qmutex.cpp`.
The baseline semaphore double opens one descriptor per object, matching the
kernel contract. It is a capacity model, not an execution of the EmberBSD kernel.
The fixed variant uses real host pthread objects.

The baseline reaches 1024 open descriptors and reports 147 allocation failures.
The same fixed pool creates 1168 objects while retaining three open descriptors.
Pool release, reuse, destruction, wake-before-wait, repeated wakeups, timeout,
a simulated timeout race, real spurious wakeups, and four concurrent consumers pass.
Injected initialization, wait, signal, and counter-overflow errors reach the
required fatal path. Cancellation releases the private event mutex. This test
does not validate complete public QMutex waiter accounting after cancellation.

The host uses its native condition clock for timed waits. A separate constructor
case checks the monotonic-clock selection with a `setclock` double. The actual
EmberBSD target configuration enables `pthread_condattr_setclock` and selects
`CLOCK_MONOTONIC`; the target contract compiles both assertions.

GCC 16.2 compiles the complete baseline and patched `qmutex.cpp` translation
units against current target headers. The target contract compares public
mutex symbols and checks the pointer-sized public QMutex/QBasicMutex layouts.
It records the compile database. These are focused module flags, not a recovered
full QtCore build configuration.

## Rebuild and public ABI boundary

Rebuild QtCore's complete `qmutex.cpp` object. That file includes
`qmutex_unix.cpp` and instantiates the free list. Install the matching private
`qmutex_p.h` with the package. Replacing only the Unix implementation object
would mix different private object sizes. The AArch64 private object grows from 24 to 104 bytes;
the 1168-object pool adds 93,440 bytes of object storage while avoiding
1168 semaphore descriptors.

The pinned qtbase archive has no other direct private-layout consumer.
`removed_api.cpp` only forwards a pointer to the public `void *` overload;
`qmutex.h` declares the opaque pointer, and the UIC map only records its name.
Public headers remain unchanged. External consumers of this private header
must rebuild; ordinary public QMutex consumers retain their ABI.

Build the public consumer against the existing unmodified Qt package before
replacing QtCore. Retain its hash and run the same binary after installation.

```sh
sh build-consumer.sh /absolute/cross-tools /absolute/emberbsd-sysroot /absolute/new-consumer
# Run on EmberBSD only after the normal updated package installation:
/absolute/new-consumer/qt-mutex-consumer
```

The consumer limits only its own descriptor table to 1024. It starts 145
contending workers, checks completion and descriptor retention, and exercises
recursive locking. Its timed waits are bounded. The deterministic pool-capacity
proof is the separate source contract; worker scheduling alone does not prove
that every private object was live at one instant.

## Validation boundary

The source contract passes ASan/UBSan on macOS/arm64. Valgrind is not available
for this host platform, so no Valgrind result is claimed. Target GCC16 object
compilation, clock and public-symbol checks pass. Clang Static Analyzer passes
on both actual source variants with target EmberBSD and GCC16 C++ headers.

Cppcheck 2.22 checks both variants with target flags, headers, and macros.
Its parser stops at the same inherited Qt 6.12 strongly-ordered declaration.
GCC-preprocessed input and its experimental Clang importer also hit parser
limits. No complete Cppcheck pass is claimed; no diagnostics are suppressed.
The separate Clang path analysis covers the complete module.

Full QtCore packaging, target condition-clock execution, the retained public
consumer, and the desktop session remain pending. These checks do not claim a
working accelerated Plasma session or a fix for a separate Mesa crash.

Sources: the pinned Qt archive in the recipe's `distinfo`,
[EmberBSD kernel semaphore implementation](https://github.com/oxtech-ember/EmberBSD/blob/main/sys/kern/uipc_sem.c),
and [descriptor allocation](https://github.com/oxtech-ember/EmberBSD/blob/main/sys/kern/kern_descrip.c).
