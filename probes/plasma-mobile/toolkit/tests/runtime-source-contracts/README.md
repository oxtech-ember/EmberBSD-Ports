# KDE runtime source contracts

These small host tests use the pinned Workspace 6.8.2 and KCoreAddons 6.31.0 archives.
They verify archive SHA512 values from the recipes before extracting source.
They verify patch SHA1 values with pkgsrc canonicalization, excluding RCS ID lines.
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
The complete KDirWatch suite and target resource-pressure checks are separate from this host contract.

Both tests run normally and with ASan/UBSan. Sanitizer errors stop the run.
On hosts without Valgrind, record that limitation; these results are not Memcheck.
Use the generated compilation database for source analysis and preserve baseline/patched results.
The initial macOS checks used Clang Static Analyzer successfully.
Cppcheck 2.22 could not parse the host SDK errno_t declaration or the target-preprocessed BSD assertion header.
Compilation-database checks with the Qt library model also hit parser errors.
Mapping the actual framework headers and compiler macros reaches an unsupported Qt `__has_builtin` condition.
Those identical baseline/patched errors are analysis limits, not clean Cppcheck results.
No diagnostic category was suppressed.

The KDirWatch recipe keeps native kqueue as the default on EmberBSD.
A failed registration now reaches the existing fallback. It does not disable monitoring.
Resource limits still belong to the session policy; this patch does not raise them.

## D-Bus result contract

```sh
ruby waiter-bus.rb /absolute/distfiles /absolute/new-output /absolute/native-qt-prefix
```

This test also requires `dbus-run-session`. It uses its own Unix-only session configuration.
It compiles the real helper `main.cpp` and `waiter.cpp` against native Qt 6.12.
Both variants include the argc fix to isolate the D-Bus result defect.
The baseline reports success for `--unregistered` when the session socket is absent.
It also reports success when a connected bus policy rejects the `NameHasOwner` query.
The patched helper returns 1 and reports the connection or query error.
A private live bus checks satisfied and pending registration and unregistration conditions.
All cases run normally and with ASan/UBSan. The test creates no persistent bus service.

This defect is separate from the constructor-local argc lifetime defect.
An absent socket did not reproduce a null-pointer crash with native Qt 6.12.
The connection guard also checks the nullable interface before use.
The test does not claim to exercise every transport-disconnection timing window.

## KDED runtime helper path

```sh
ruby kded-runtime-path.rb /absolute/distfiles /absolute/new-output
```

The KDED 6.31.0nb1 recipe separates its runtime helper from native build tools.
A cross build uses `KDE_INSTALL_FULL_LIBEXECDIR_KF/kconf_update` on the target.
Native builds retain the upstream `KF6::kconf_update` target-file selection.
KConfig still installs the target helper and supplies native tools for code generation.

The test verifies the archive and patch hashes before applying the patch.
It evaluates the real `src/CMakeLists.txt` with external framework targets and generators doubled.
The baseline embeds the imported host executable in three cross configurations.
The patched source selects the target path with the default prefix, a prefix with spaces,
and a separate libexec directory. Native target selection passes in both variants.
The generated compilation database contains the actual `kded.cpp` target.
This is a CMake source contract. It does not compile KDED or execute its target helper.
No C++ implementation changes are involved. Package and target execution remain separate checks.

## Installed CM5 checks

Workspace 6.8.0nb3 and KCoreAddons 6.31.0nb2 pass installed package checks for 6308 files.
The actual wait helper passes four cases under an existing non-root user.
Missing-bus registration and unregistration return 1; satisfied conditions on a private live bus return 0.
The cross-built upstream KDirWatch default and Stat suites each pass all 19 cases, without skips.
The default suite uses the native Qt/kqueue backend. The Stat suite checks the existing fallback.
These are component checks. A later desktop launch still reports descriptor exhaustion in child services.
The current tests do not establish full-session resource stability.

## Installed KDED helper check

```sh
timeout 30 sh kded-runtime-path.sh /absolute/new-output
```

Run as the desktop user with installed KDED and KConfig. The optional second argument is the package prefix.
The check uses the offscreen Qt platform and new HOME/XDG directories.
It invokes `kded6 --check` with a private version-6 update script.
The script writes a marker through the actual target `kconf_update` process.
The runner checks that marker because upstream KDED returns zero even when helper execution fails.
On CM5, the old package fails this check because it embeds the host build path.
The full 6.31.0nb1 package passes the same private update under an ordinary user.
Its 22 installed files, automatic mark and reverse dependencies are verified.
This accepts the runtime helper path, not all KDED modules or a full desktop.
It does not contact the desktop bus or use the user's configuration.
Keep the output directory as evidence until the result is reviewed.
