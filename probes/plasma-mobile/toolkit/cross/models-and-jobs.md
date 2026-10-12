# Frameworks models, jobs, colors and session services

KItemModels, ThreadWeaver and KCrash 6.31.0 cross-build with the common
Qt 6.12/GCC16 stack. Their complete packages pass the ordinary manifest,
dependency, interpreter, permission, PIE, RELRO, RPATH and work-reference
checks. EmberBSD Ports owns these recipes and the following test runners.

## Cross-host corrections

ThreadWeaver installs both `ThreadWeaver/Job` and `threadweaver/job.h` below
its public include root. A case-insensitive macOS staging filesystem merges
the directory names. The original pkgsrc extra-file check then rejects valid
headers even though its archive writer uses the correct PLIST spelling.
The [common helper](../../../../profiles/common-build-tools/cross/check-files-case.sh)
normalizes only the added-file comparison on such cross hosts. It retains
unlisted files and rejects distinct target files that collide after case
folding. Case-sensitive stages are unchanged. No file check is disabled.
The source regression reproduces the mismatch, retains an extra-file error,
and rejects collisions without modifying the original comparison input.

KWindowSystem and KGuiAddons buildlinks now follow Qt 6.12's move of
WaylandClient into Qtbase. The real KCrash/KColorScheme dependency graph
passes `tests/wayland-client-deps.sh`; restoring the previous buildlinks
makes that check fail. KCrash's ordinary package build also succeeds.

## Run against installed packages

Copy original upstream test binaries from each `_KDE_build/bin` to the target.
For KItemModels, place its private `libproxymodeltestsuite.so` in a sibling
`lib` directory containing no other libraries. For KCrash, copy `test_crasher`
and the original `autotests/core_patterns` directory beside the test binaries.
The test runners require installed target Qt/KF packages and `timeout`.

```sh
sh tests/itemmodels-runtime.sh /absolute/itemmodels/bin /absolute/new-model-results
sh tests/threadweaver-runtime.sh /absolute/threadweaver/bin /absolute/new-job-results
sh tests/kcrash-runtime.sh /absolute/kcrash/bin /absolute/new-crash-results
```

Paths above are relative to this toolkit's root. The runners isolate settings,
bound each test and check that the board has not rebooted. KItemModels' only
loader override selects the upstream private test helper; Qt/KF libraries
come from installed packages. ThreadWeaver also compiles a native consumer
including both public header spellings. KCrash disables core dumps for the
intentional test crashes; no kernel fault is requested.

## CM5 evidence, 2026-10-12

CM5 Rev 1.0, BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B, with kernel SHA256
`6c5aa74d3c33fb6e84ea5c04d6f3df48928deb021cdc908ee972a42df03c7bf5`:

- KItemModels: all 13 original test processes exit successfully. QtTest totals
  are **500 passed, zero failed and six upstream skips**; BiHash also exits zero.
- ThreadWeaver: all seven original test processes pass, **77 QtTest cases**,
  covering queues, sequences, lifecycle, abort, shutdown and object deletion.
  Both header directory spellings compile on the case-sensitive target.
- KCrash: **16 QtTest cases** pass for intentional crash/restart, emergency save,
  metadata and core configuration. The board boot identity is unchanged.
  DrKonqi and desktop integration remain untested.

| Artifact | SHA256 |
| --- | --- |
| KItemModels package | `bc78e02c54304d3bf60e009a952a29a4394db7235d80eeedc44c2ea5894a579e` |
| ThreadWeaver package | `f3eaa74a760acb5f4a0716c6fac40f6d7a4e7c46cfc3b67e7b2797b7222fff3d` |
| KCrash package | `0bc16cf5a205a04dba2f1d22de097d1aa281630efa615c3955c7fb59eca5258c` |
| KItemModels target journal | `0579a8b3fbdd57e0b20ce351f0f6a3986f8eab02c26ff261bb8cd85f936bcc35` |
| ThreadWeaver target journal | `38ef21a9ac147618f38fb67b261dc28c69ff1787bd90672463f1706d04f95d3e` |
| KCrash target journal | `daf8ddc195f186bfbf457a3d60cbccb24e6a86155566c5d29caa94b6e2b9df47` |

These short runs establish model APIs and worker-queue behavior. They do not
measure compositor latency or long-duration stability. QtTools runtime, KWin,
Plasma, HDMI output and a remote accelerated desktop remain separate gates.

## Color schemes and D-Bus on the same CM5

KColorScheme 6.31.0 and KDBusAddons 6.31.0nb1 pass ordinary full package
checks and install in the shared sysroot and on the board above.
KColorScheme's 12 original QtTest cases pass with zero failures or skips.
Copy its original `kcolorschemetest.colors` beside the binary; omitting
upstream data is a failed test setup, not a library failure.

KDBusAddons passes its original `deadservicetest` (three QtTest cases) and
`kdbusservicetest`. The latter runs with `QT_FORCE_ASSERTS` and checks three
activations, propagated failure status 4 and successful child termination.
The dead-service test intentionally stops and terminates only its own helper;
upstream emits two QProcess destructor warnings after asynchronous kills.
Each executable gets a fresh private D-Bus session and isolated settings.
Boot identity stays unchanged. These are short API tests, not desktop acceptance.

```sh
sh tests/colorscheme-runtime.sh /absolute/colors-binary-and-data /absolute/new-colors-results
sh tests/kdbusaddons-runtime.sh /absolute/dbus-test-binaries /absolute/new-dbus-results
```

Copy `deadservicetest`, `kdbusservicetest` and `kdbussimpleservice` from the
upstream build. The installed D-Bus default policy must work: these runners
do not substitute a private configuration. [D-Bus nb5](../../../../profiles/common-graphics/cross/desktop-support.md)
fixes the cross-host socket-directory leak that the original CM5 run exposed.
KDBusAddons only needs native Linguist tools during the cross build; its
recipe retains target QtCore/DBus/Gui and does not require target QtTools.
The real dependency and native-tool version guard passes for both KCoreAddons
and KDBusAddons, including missing and outdated tools.

| Artifact | SHA256 |
| --- | --- |
| KColorScheme package | `beebca0f7013cc5aeaf3287c595567e3c4457e27ae3dd0586ca15bc975cf7c8e` |
| KColorScheme journal | `f2e98cfe055c34cbfffdbab79efdaff8ab09a2f99fd10be21577b70143870728` |
| KDBusAddons package | `8fdbc8d62604c9f9a75d972850c71b9ba98f0c125969f061b28eedd2d2d43c1f` |
| D-Bus/KDBusAddons target journal | `3d8a43c7171ddaf97caf8138908e941f245406a0f05bbac6e13c5753dfb06f96` |

## Widget APIs and the Designer plugin

KWidgetsAddons 6.31.0nb1 cross-packages with the complete target Designer
plugin. Upstream's cross-build conditional disabled it despite the package
manifest requiring it. The patch uses the normal user-selectable option;
native defaults stay unchanged. `tests/widgets-plugin.rb` reproduces the
original exclusion, checks both defaults and inspects the installed AArch64
plugin. QtTools supplies build-time interfaces; the actual plugin links
KWidgetsAddons and Qtbase, so it does not impose a runtime QtTools dependency.
The final package manifest was checked after rebuilding the dependency cache.

On the same CM5, four original upstream executables pass **54 QtTest cases**,
zero failures and no skips: date combo (11), time combo (19), dual action (6)
and select action (18). They use the installed shared library with the minimal
QPA plugin, isolated settings and no loader override. Copy those four binaries
from `_KDE_build/bin` and run:

```sh
sh tests/widgets-runtime.sh /absolute/widget-test-binaries /absolute/new-widget-results
```

Package SHA256: `6003f318ac633add438cb93a30c70ac16cbc8104ac864bc41276e2455d9d45b8`.
CM5 journal: `c47b7a20c6a49efb9c9fc9879b4e66cae9812793f5231b5425247bcf6fc63461`.
Cross-plugin regression: `f7825f76328576f0bb72f10bb6b9569ead115adc475fb8be4103ca264507f7dd`.
These tests establish widget APIs. Designer loading, physical input, GPU
presentation and the other widget tests remain unaccepted.
