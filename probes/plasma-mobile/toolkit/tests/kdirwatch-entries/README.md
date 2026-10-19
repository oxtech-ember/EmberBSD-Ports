# KDirWatch entry lifecycle

KCoreAddons 6.31.0nb4 snapshots dependent paths before it scans them recursively.
Each scan looks up the path again. A scan can remove a child from its parent's
list and delete a parent that has no clients. The event handler also registers
a file again only while the file exists. Repeated events for a missing file
must not add the same parent dependency again.

The change preserves the nb3 descriptor budget, Stat fallback, public headers,
and exported API. It changes the QFileSystemWatcher event path only.

## Reproduce

Use Ruby 2.6 or later, CMake 3.30 or later, Ninja, patch, tar, native Qt 6.12, and ECM 6.31.
The output directory must be new. The runner builds the complete upstream
KF6CoreAddons library. It needs no target sysroot.

```sh
ruby probes/plasma-mobile/toolkit/tests/kdirwatch-entries/run.rb \
  /absolute/distfiles/kcoreaddons-6.31.0.tar.xz \
  /absolute/new-output /absolute/native-qt \
  --ecm-dir /absolute/ECM/cmake --jobs 2
```

Use `--cmake /absolute/cmake` if CMake is outside PATH.
The runner verifies the archive, all current recipe patches, and the retained
nb3 patch. It applies the patches with zero fuzz. `source.json` records source
and test hashes. `commands.json` records commands and exit statuses. Each command
has separate standard-output and standard-error files.

The test uses the existing upstream friend class to inspect real Entry objects.
It creates real files and uses the actual Qt containers, QObject calls,
QFileSystemWatcher, scanEntry, addEntry, removeEntry, and registration methods.
It invokes the real event slot directly to control event order. Only the
KDirWatch translation unit selects the NetBSD backend policy after the native
Qt configuration has loaded. Qt itself keeps its native platform backend.

The three cases check:

- Four missing children become present during a parent event. All children
  must become Normal and retain one client registration.
- Repeated events for a missing file retain one parent dependency and one
  client registration.
- Creation of all children removes the parent that has no clients. All
  children must remain registered and become Normal.

The retained nb3 source must abort at each intended fatal CHECK. The candidate
must pass all three cases. Two compiled controls restore the live child-pointer
loop or missing-file re-registration separately. They must abort at the
corresponding CHECK. An unrelated crash does not count as the expected result.
The candidate also passes all three cases with AddressSanitizer and
UndefinedBehaviorSanitizer. The normal build is restored to the candidate.

The separate [descriptor-budget regression](../kdirwatch-budget/README.md)
must also pass with this patch. Its accounting and fallback controls remain
independent of these lifecycle checks.

## Verification boundary

These checks cover the complete native library with real Qt services and a
controlled call to the event slot. They do not prove native NetBSD kqueue
delivery, a target package, an installed-library scenario, or a Plasma session.
Cross-build target packages with GCC16 and verify those boundaries separately.

Paired Clang Static Analyzer and Cppcheck runs use the actual native compilation
command and full baseline and candidate KDirWatch translation units. Preserve
parser limitations and inherited findings when comparing results. A parser
failure is not a clean analysis result. Valgrind does not support the Darwin
AArch64 host used for the native run; ASan/UBSan are substitutes.

On the tested native host, CSA reports the same inherited Qt invokeMethod
ownership warning in nb3 and nb4. Cppcheck stops at the same Q_DECLARE_FLAGS
framework-macro boundary in both direct runs. Both compiler-preprocessed runs
stop at the host SDK errno_t declaration. No diagnostic category is suppressed.

## Target acceptance

The nb4 package was cross-built for EmberBSD AArch64 with GCC16 16.2.0 and
LLD 23.1.3. Its archive audit passed. It retained all 207 payload paths and
77 unchanged public headers.
The library kept its 804 exports and the QML plugin kept its 17 exports,
including symbol types, binding, visibility, object sizes and version names.
SONAME and dependency checks passed. The target sysroot was unchanged.

The same target lifecycle executable reached each intended CHECK with installed
nb3, then passed all three cases with installed nb4. Private headers, feature
configuration and dependency headers matched across the two builds. The existing
installed descriptor-budget consumer also passed. The lifecycle checks still
control the event-slot call; they do not prove native kqueue event delivery.

One installed Plasma session passed readiness, 30-second liveness and normal
logout checks with hardware V3D, Wayland, Xwayland, Activities and the desktop.
The output was a virtual 1280x1024 display. This check does not cover HDMI, KMS,
hotplug, input or a long stress run.

Paired analysis of the actual target translation unit used GCC16 preprocessing
with the target sysroot. Cppcheck stopped at the same target assert.h parser
boundary in both versions. CSA with target headers reported the same inherited
Qt invokeMethod warning. Analysis of GCC-expanded C++ also hit GNU16 builtin
limits. These parser limits are not clean analysis results.
