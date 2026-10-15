# KDE runtime source contracts

These small host tests use the pinned Workspace 6.8.0 and KCoreAddons 6.31.0 archives.
They verify archive SHA512 values from the recipes before extracting source.
They do not run a desktop or accept GPU rendering.

```sh
ruby run.rb /absolute/distfiles /absolute/new-output /absolute/native-qt-prefix
```

Use native Qt 6.12 with Core, CorePrivate, DBus, and its matching moc.
Use CMake, a C++20 compiler, and Ruby. The runner uses at most two build jobs.
It builds the real upstream `waiter.cpp`, with baseline and Ports-patched headers.
It compares the Qt-private argc reference address with the caller's live argc.
The baseline fails before reading expired storage. The patched helper also checks
`arguments()`, `applicationFilePath()`, and `applicationDirPath()` after construction.
Qt's constructor contract requires argc and argv storage to outlive the application.

The KDirWatch test extracts `useQFSWatch`, `useStat`, and `addWatch` without editing their bodies.
The registration boundary returns a controlled failure with EMFILE.
The baseline falsely reports success. The patched source selects the existing Stat mode and starts its timer.
The test also checks successful registration, existing file/directory watches, and missing-path parent watches.
Only the external watcher, filesystem classification, and timer boundaries are doubled.
This verifies fallback selection, not real filesystem notifications.
The complete KDirWatch suite and target resource-pressure checks remain separate requirements.

Both tests run normally and with ASan/UBSan. Sanitizer errors stop the run.
On hosts without Valgrind, record that limitation; these results are not Memcheck.
Use the generated compilation database for source analysis and preserve baseline/patched results.
The initial macOS checks used Clang Static Analyzer successfully.
Cppcheck 2.22 could not parse the host SDK errno_t declaration or the target-preprocessed BSD assertion header.
Those identical baseline/patched parser errors are analysis limits, not clean Cppcheck results.
No diagnostic category was suppressed.

The KDirWatch recipe keeps native kqueue as the default on EmberBSD.
A failed registration now reaches the existing fallback. It does not disable monitoring.
Resource limits still belong to the session policy; this patch does not raise them.
