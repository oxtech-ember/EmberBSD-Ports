# Plasma D-Bus client support on EmberBSD

This diagnostic probe builds ModemManagerQt, NetworkManagerQt, and
BluezQt 6.26.0, QtKeychain 0.17.0, and plasma-nm 6.7.5 against Qt 6.11.1.
The shared Plasma 6.7.5 installation is a separate prerequisite. The planned
final baseline is GCC 16.2, Qt 6.12.0 LTS, and KF6 6.31; this probe does not
validate that future baseline or establish a permanent older dependency.
These are real Qt D-Bus client libraries. No Linux daemon is implemented or
installed. A successful build does not provide modem, Wi-Fi, mobile-data,
suspend/resume, Bluetooth, or NetworkManager service support.

The version follows the installed package cohort; it is not a claim that
6.26.0 is the newest upstream release. The existing ModemManager 1.24.2
client prefix is reused. NetworkManager's 1.54.3 public headers use the
same version as the existing Phosh portability probe. No substitute
library is installed. The diagnostic prefixes must be superseded when the
common dependency stack is rebuilt on the selected final baseline.

## Build

Use an ordinary user on NetBSD 11/aarch64. Required packages include the
matching Qt 6 development modules, ECM 6.26.0, CMake 3.29 or newer, Ninja,
GLib/GIO development files, OpenSSL, QCoro, matching KF6 development
packages, Prison/QuickCharts/Kirigami Addons QML modules, pkg-config,
D-Bus tools, curl, Meson, xsltproc, xmllint, and the compiler.
The recipe also builds the original GNOME operator database release
`mobile-broadband-provider-info` 20251101 for its upstream data test. Its
upstream Meson version field remains 20240407; the pinned tag and source
archive identify the actual data release.
GLib's upstream `glib-mkenums` uses Python; this probe adds no Python helper.
The KDE build system also discovers the installed Python interpreter.

First build the real ModemManager client using the existing Ports
[Phosh client-libraries recipe](../../phosh/client-libs/README.md).
Set `MM_PREFIX` to its resulting `prefix` directory.
Set `PLASMA_PREFIX` to the current shared Plasma 6.7.5 installation:

```sh
MM_PREFIX=/absolute/path/to/modemmanager-client/prefix \
PLASMA_PREFIX=/absolute/path/to/current-plasma/install \
JOBS=1 sh probe.sh /absolute/path/to/archive-cache
```

Omit the last argument to download directly from upstream. All archives
are checked against pinned SHA256 values before extraction. `WORK_DIR`
may select a new absolute build directory; it must not already exist.
Sources, artifacts, and logs remain in that private directory. The script
preserves failures and does not install system packages or start services.
This diagnostic cohort pins `/usr/bin/cc` and `/usr/bin/c++` in every build
helper and CMake configuration. Caller-provided compiler variables cannot
select a different C++ runtime. The final toolchain transition requires
rebuilding the shared dependencies and updating this diagnostic contract.

Consumers use the resulting `prefix` in `CMAKE_PREFIX_PATH` and its
`lib/pkgconfig` in `PKG_CONFIG_PATH`. There is no fake `libnm.pc` or
`libnm.so`. The `networkmanager-headers.pc` file advertises only original
public declarations, constants, and GIO's required include flags.

## Why NetworkManager headers are sufficient

NetworkManagerQt implements its D-Bus calls using QtDBus. Its source
contains no calls to `nm_*` functions; the only such textual match is a
comment referencing upstream `nm_utils_security_valid`. Its use of
NetworkManager is public types, enumerators, and property-name constants.
The original CMake build nevertheless requests and links libnm.

The opt-in `NETWORKMANAGERQT_HEADERS_ONLY` option substitutes the explicitly
named `networkmanager-headers` metadata for the normal `libnm` dependency.
It preserves the full KDE library, QML plugin, and upstream unit tests.
The default upstream path still selects real libnm. Installed CMake
configuration propagates the selected dependency to downstream clients.

`install-networkmanager-headers.sh` copies the original 1.54.3 public
headers, substitutes the three version numbers in the upstream version
header template, and invokes upstream GLib enum generation. It preserves
upstream notices and copies the source license files. The upstream
`NM_NO_INCLUDE_EXTRA_HEADERS=1` option avoids unused Linux system headers
normally included for historical compatibility.

This does not make GLib libnm itself portable. Its separate build still
has Linux-specific implementations; it is neither built nor advertised
by this probe.

## Local patches

All seven patches are local, AI-assisted EmberBSD changes. They have not
been submitted to or accepted by upstream. Original source copyright,
SPDX identifiers, and licenses are retained.

- `modemmanager-qt-prefix-includes.patch` propagates the parent of the
  pkg-config include directory. KDE's public headers use the nested
  `<ModemManager/ModemManager.h>` spelling, so a non-system prefix needs
  both include directories. The path must reach Qt moc as well as the C++
  compiler; otherwise moc can omit version-conditional SIM signals. No modem
  implementation changes.
- `networkmanager-qt-headers-only.patch` adds the optional honest headers
  dependency and exports it through the installed CMake target. GIO is
  needed only for public declarations in this mode; no GIO runtime calls
  exist, so `Requires.private` carries its headers without linking it.
- `networkmanager-qt-clock.patch` selects the existing `CLOCK_MONOTONIC`
  fallback at compile time when `CLOCK_BOOTTIME` is absent. It also avoids
  reading an uninitialized timestamp when `clock_gettime` fails. This
  establishes only the monotonic-clock conversion used by this build;
  Linux boot-clock equivalence across suspend is not claimed.

- `plasma-nm-dbus-client-only.patch` introduces an explicit QML-client build.
  It keeps the real editor library, network models, QtDBus operations, and
  new cellular QML module. It omits the desktop applet, KDED service, KCMs,
  and VPN import plugins that require libnm's object implementation. The
  unused C++ `NMConnection` import overload is excluded, not replaced.
  Local libnm VPN-plugin preflight is omitted; ordinary QtDBus calls still
  return their real errors. The normal upstream build remains the default.

- `bluez-qt-netbsd-endian.patch` selects NetBSD's real byte-order macros
  for BlueZ's inherited A2DP codec bitfields. The Linux branch is unchanged.
  A native C contract checks the exact four-byte SBC wire representation
  with undefined preprocessor identifiers treated as errors.

- `bluez-qt-rfkill-linux-only.patch` extends the existing Linux guards to
  the new private rfkill worker class and its field. Non-Linux builds retain
  upstream's Unknown rfkill state; no worker or simulated device is added.

- `plasma-nm-provider-data-20251101.patch` updates two exact upstream test
  expectations for the pinned current database: sipgate also uses 26203,
  and Willkommen also uses 26202. The original XML confirms both entries.
  Full list equality remains checked; no database or production code changes.

BluezQt's build does not establish BlueZ or rfkill support on NetBSD. QtKeychain 0.17.0
uses the existing Qt 6 ABI and is selected before the system's old package
for this current Plasma stack; no second old ABI is introduced.

`KF_IGNORE_PLATFORM_CHECK=ON` is KDE's supported opt-in for compiling a
platform not yet listed by the project. It does not suppress compiler
or linker errors.

On this NetBSD image, QtNetwork loads the base GSSAPI/Heimdal libraries,
which lead GNU ld to warn about existing compatibility aliases in
`libutil.so.7`. The NMQt, BluezQt, and plasma-nm recipes keep those warnings visible
but pass `--no-fatal-warnings` after ECM's global fatal-warning option.
The `--no-undefined` link check remains enabled. This does not resolve
or conceal the underlying base-library compatibility warnings.

## Validation

The helper builds the shared client libraries and executes the original
ModemManagerQt/NetworkManagerQt CTest suites under a private D-Bus session.
BluezQt's manager and QML suites are selected, while plasma-nm runs its
address-validation and operator-data tests. Their upstream fake
service fixtures are used only for tests and are not installed as runtime
services. Serial execution avoids fixtures competing for D-Bus names.

`verify-client.sh` compiles fresh consumers against the installed exported
CMake targets. Each run has separate XDG configuration, data, cache, and
runtime directories; the account's `HOME` remains unchanged. Each consumer
runs under a private session bus with immediate symbol binding, a timeout,
and required positive result markers. Logs remain in
`client-verification.*/logs` beneath the selected work directory.

Before constructing any MMQt, NMQt, or BluezQt client, the native probe
queries the existing system bus for both owned and activatable service names.
It rejects any matching daemon, unavailable bus, or failed query. The QML
probe repeats this preflight before importing the four real modules and
runs only after the native probe succeeds. These are preflight snapshots;
the system bus configuration must remain unchanged during verification.
Private fixture buses test all three names, both consumers, query denial,
and an unavailable bus without installing or starting real daemon services.

The real clients must report no devices or adapters. The probe also checks
non-operational BluezQt initialization and the clock conversion. QtKeychain
is checked only through its read-only `isAvailable()` API; no credential
jobs run. A backend availability result does not validate credential storage.

The NetBSD `ldd` gate requires exactly one base `/usr/lib/libstdc++.so.9`
and no missing library in each of 13 ELF dependency closures: both consumers,
seven shared libraries, and all four QML plugins. Parser regressions reject
wrong paths, wrong versions, mixed runtimes, missing libraries, and an absent
C++ runtime. Dynamic-dependency and undefined-symbol checks also exclude an
accidental libnm runtime dependency.

These checks do not establish any physical network or modem operation.
No active graphical session, host console, or hardware is modified.

### Observed validation on 2026-10-06

The shared libraries and all four QML modules built and installed on
NetBSD 11/aarch64 with the EMBER64 kernel, base GCC 12.5.0, Qt 6.11.1,
and KF6 6.26.0. The loaded C++ runtime was base `libstdc++.so.9`.

| Check | Result |
|---|---|
| plasma-nm CTest | 5/5 passed, including AppStream, three IP validators, and the operator database test with updated expectations |
| Original provider-data tests | XML validation passed; the whitespace search returned its expected no-match status |
| Installed CMake consumer | Passed: no owned or activatable daemon names, no devices, non-operational BluezQt initialization, clock conversion |
| Original QML plugins | All four modules imported successfully using the offscreen platform |
| C++ runtime gate | All 13 ELF dependency closures passed; 6 parser regression cases passed |
| Service preflight regressions | 16 cases passed: owned/activatable names, query denial, and unavailable bus for both consumers |
| Compiler selection | Native verifier passed with deliberately invalid inherited `CC`/`CXX`; its fresh build used `/usr/bin/c++` |
| Native A2DP SBC layout | Passed with `-Werror=undef` |
| libnm dependency/symbol check | No direct libnm dependency or unresolved `nm_*` calls in NMQt or the three plasma-nm libraries |
| QtKeychain availability | Read-only call reported an available backend in the isolated profile; credential storage was not tested |
| Full MMQt/NMQt and selected BluezQt suites | Pending: their separate test targets were held for coordinated VM build capacity and toolchain work |

The pending suites must not be reported as passed. Existing objects and
logs are retained; resume their `build-*.sh` helpers with `JOBS=1` and
`CLIENT_LIBRARIES_ONLY` unset. The observed checks precede the planned
system-wide toolchain transition and do not validate that later ABI.
The final verification used unchanged account `HOME` and isolated XDG
directories. Its `logs/client-artifact-sha256.log` records seven installed
library hashes inside that run's `client-verification.*` directory.

## Pinned sources

| Archive | SHA256 |
|---|---|
| [modemmanager-qt-6.26.0.tar.xz](https://download.kde.org/stable/frameworks/6.26/modemmanager-qt-6.26.0.tar.xz) | `bef456ac0a5983bcc14a1580cb0d32a001241f380d901cb503613855380af3a5` |
| [networkmanager-qt-6.26.0.tar.xz](https://download.kde.org/stable/frameworks/6.26/networkmanager-qt-6.26.0.tar.xz) | `a5cfed06af6156161f7fee56efe1521a6e9e26119327069f1799986f90b432e5` |
| [NetworkManager-1.54.3.tar.gz](https://gitlab.freedesktop.org/NetworkManager/NetworkManager/-/archive/1.54.3/NetworkManager-1.54.3.tar.gz) | `16c1e954a8598a0afc71c9936a7e4f0ad949522438d96fec63aa1abb6f2207fe` |
| [bluez-qt-6.26.0.tar.xz](https://download.kde.org/stable/frameworks/6.26/bluez-qt-6.26.0.tar.xz) | `ebeb301eaeb6ec6729b27969556839165ba582ebe242b42cde71c8faa80d63df` |
| [qtkeychain-0.17.0.tar.gz](https://github.com/frankosterfeld/qtkeychain/archive/refs/tags/0.17.0.tar.gz) | `3b85c3929034b0a99da777130c34d99f006fcd3a9d56564159399a33fee0e504` |
| [plasma-nm-6.7.5.tar.xz](https://download.kde.org/stable/plasma/6.7.5/plasma-nm-6.7.5.tar.xz) | `6469ff89e26d44565292c968df595b3a68f353707255ba48725c1bae2a67f3be` |
| [mobile-broadband-provider-info-20251101.tar.bz2](https://gitlab.gnome.org/GNOME/mobile-broadband-provider-info/-/archive/20251101/mobile-broadband-provider-info-20251101.tar.bz2) | `6fa60b5e9860a648d7c5b8e4e3f87d6ce6a7622b8a7b5f2d567a9a0d9dddb9f7` |

KDE archive hashes were also checked against the published adjacent
`.sha256` responses. Source downloads and full build logs are not tracked.
