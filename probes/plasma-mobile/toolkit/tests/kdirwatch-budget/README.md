# KDirWatch descriptor budget

The NetBSD backend of KCoreAddons 6.31.0nb4 retains a finite per-watcher budget.
Qt's kqueue backend opens one descriptor for each watched path.
The budget counts unique files and directories already held by QFileSystemWatcher.
It allows at most half the current soft `RLIMIT_NOFILE` limit.
Additional entries use the existing Stat timer and change-detection backend.
This budget does not reserve descriptors across all watchers or the whole process.

Existing paths do not consume another slot. Removed paths restore capacity.
Failed registrations keep the existing fallback behavior.
An unavailable, infinite, or unusably small limit selects Stat with a warning.
Polling entries remain on Stat during re-registration and queued file events.
This preserves `statEntries` and timer accounting.
The file-event path uses the same registration policy.
The nb4 [entry lifecycle regression](../kdirwatch-entries/README.md) also checks
recursive scans and missing-file events against the complete native library.
Other platforms keep their previous selection.

## Actual-source regression

Run with the pinned upstream archive and a native Qt 6.12 installation:

```sh
ruby probes/plasma-mobile/toolkit/tests/kdirwatch-budget/run.rb \
  /absolute/distfiles/kcoreaddons-6.31.0.tar.xz \
  /absolute/new-output /absolute/native-qt
```

The runner verifies the archive, production patch, and retained nb2 patch hashes.
It extracts the complete production `useQFSWatch`, `useStat`, `addWatch`, and
`fswEventReceived` methods. The fixture doubles the watcher, resource-limit,
timer, scan, and notification boundaries. It uses real Qt containers.
It does not simulate a complete operating-system filesystem watcher.

The accepted nb2 source fails at the exact mixed file-and-directory budget.
The fixed source passes normal, AddressSanitizer, and UndefinedBehaviorSanitizer runs.
Five mutants test missing budget, files-only counting, the boundary comparison,
unstable Stat accounting, and direct file-event registration.
Each mutant must fail at its intended assertion with exit status 1.
A signal or sanitizer diagnostic does not count as an expected failure.

The cases cover an existing path at a full or lowered limit, path removal,
repeated registration, registration failure, and subsequent successful registration.
They also cover zero, one, infinity, failed `getrlimit`, missing paths,
and repeated file events on an entry that switched to Stat.

## Acceptance boundary

These checks prove method control flow and accounting with explicit doubles.
They do not prove recursive traversal, real filesystem events, or process-wide
file-descriptor capacity. Target compilation and installed-library tests must
also cover a real directory tree, changes below polling directories, and live
file-descriptor counts. Complete Plasma acceptance remains separate.

Clang Static Analyzer and Cppcheck use the actual native fixture commands for
both nb2 and fixed methods. The fixture's value-return accessors intentionally
match QFileSystemWatcher's API. They retain two Cppcheck performance suggestions.
Other retained style reports concern inherited methods and explicit test doubles.
Full target translation-unit analysis belongs to the target package build.
Valgrind does not support this Darwin AArch64 test host; ASan/UBSan are substitutes.

## Native public consumer

Cross-build `runtime.cpp` with the selected GCC16 compiler and the common
EmberBSD sysroot. Include the installed `KF6/KCoreAddons`, `QtCore`, and Qt headers.
Link `KF6CoreAddons`, `Qt6Core`, and pthread with the current LLD23 selection.
Use the normal `/usr/pkg/lib`, `/usr/pkg/qt6/lib`, and GCC16 runtime search paths.
The consumer uses public APIs. Keep the same binary for the nb2 and nb3 comparison.

Build from the development host with the selected GCC16-to-LLD23 specs file:

```sh
ruby build-runtime.rb /absolute/cross-tools /absolute/emberbsd-sysroot \
  /absolute/selected-linker.specs /absolute/new-consumer
```

The builder checks the compiler target, compiler/linker versions, AArch64 ELF,
interpreter, actual linker marker, and unchanged input hashes.
On the target, run the retained binary with a new output path:


```sh
timeout 90 sh runtime.sh /absolute/kdirwatch-budget /absolute/new-result
```

The runner clears inherited library and Qt overrides. It records package identity,
loaded dependencies, input hashes, the runtime log, and the actual exit status.
The consumer sets and verifies soft `RLIMIT_NOFILE=1024` in its own process.
An insufficient or unbounded enumeration limit returns 77 with a stated reason.
The fixture requires a finite hard limit between 1024 and 65536.
It never changes the caller's limits or global kernel limits.

The consumer creates 600 directories and 600 files before it registers any watch.
It records the descriptor count before it attempts a further recursive tree.
Only `FAIL: native watch FD budget exceeded` with exit 1 is the expected nb2 cause.
An unrelated setup error, signal, or timeout is a failed test, not that baseline.
The candidate must retain capacity to open an ordinary file.
A nested file in the later recursive branch must report content changes,
rename, deletion, and recreation. Repeated events must not grow native descriptors.
Watcher destruction must release path descriptors. The fixture then removes its own tree.
## CM5 package acceptance

The same AArch64 consumer ran on CM5 before and after the complete nb3 package.
Its SHA256 is `ef9f1ca2dfbfc53ec7deb8aaa6b568f1c70ad2cec4f637c54550323d13612c98`.
With nb2, descriptors increased from 4 to 1024. The exact budget assertion failed.
With nb3, 1200 paths used 519 descriptors. Repeated polling events kept that count.
Watcher destruction restored the original 4 descriptors. The ordinary file open,
recursive change, rename, deletion, and recreation checks passed.

The complete package has 207 payload files. Its SHA256 is
`e7c123e4ddebd1d9e27edb3e64dc24ed56815518704dd553258406a6479dd3e0`.
Installation verified those files, the full dependency graph, and the automatic mark.
The public headers, API exports, and SONAME remained compatible with nb2.
This is a per-watcher regression. It does not prove a process-wide descriptor
reserve or a stable full Plasma session.

GCC16 `-fanalyzer` passed the actual target translation unit. Clang Static Analyzer
reported an inherited Qt connection-ownership warning; inspected ownership code
contradicts that report. Target-preprocessed Cppcheck stops at the inherited BSD
assertion header in both variants. This is an analysis limitation, not a clean
full-unit result. The source fixtures above retain their separate analyzer scope.
