# KDirWatch descriptor budget

The NetBSD backend of KCoreAddons 6.31.0nb3 uses a finite per-watcher budget.
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
